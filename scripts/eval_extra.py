"""Checks beyond the panel key: the maintainer's own pair picks, Brown Bag levels, and CPU speed.

  eval_extra.py work/multi/m400.pt [work/multi/s68.pt ...] [--speed]

pairs:    scoring/pairs.csv, the maintainer's pick of the stronger of two statements (a, b or same).
          Reported: how often the model's overall score picks the same one, over pairs with a pick.
brownbag: work/brownbag_scored.csv, levels from Brown Bag Lessons; Spearman rho with the level head.
speed:    int8 (dynamic quantization) on 4 CPU threads, ms per statement at 40 and 128 tokens.
"""
import csv, json, os, sys, time

import numpy as np
import torch
from scipy.stats import spearmanr
from transformers import AutoTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multi_data as M
from train_multi import load_model, predict

ROOT = M.ROOT
LEVEL = {"membership": 1, "supervisory": 2, "management": 3, "leadership": 4, "fluff": 0}


def texts_by_id():
    df = M.bank()
    t = {str(r): x for r, x in zip(df.rid, df.text)}
    for r in csv.DictReader(open(os.path.join(ROOT, "work", "brownbag_scored.csv"), encoding="utf-8", errors="replace")):
        t["bb" + r["line"]] = r["text"]
    return t


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    speed = "--speed" in sys.argv
    t = texts_by_id()
    pairs = [r for r in csv.DictReader(open(os.path.join(ROOT, "scoring", "pairs.csv"), encoding="utf-8"))
             if r["left"] in t and r["right"] in t]
    bb = [r for r in csv.DictReader(open(os.path.join(ROOT, "work", "brownbag_scored.csv"), encoding="utf-8", errors="replace"))
          if r["level"] in LEVEL]
    ov = M.SCORES.index("overall"); lv = M.SCORES.index("level")
    for ck in args:
        m, cfg = load_model(ck)
        tok = AutoTokenizer.from_pretrained(cfg["base"])
        res = {"model": os.path.basename(ck)}
        L = predict(m, tok, [M.norm(t[r["left"]]) for r in pairs])["score"][:, ov]
        R = predict(m, tok, [M.norm(t[r["right"]]) for r in pairs])["score"][:, ov]
        by = {}
        for r, a, b in zip(pairs, L, R):
            if r["pick"] in ("a", "b"):
                hit = (a > b) == (r["pick"] == "a")
                by.setdefault(r["kind"], []).append(hit); by.setdefault("all", []).append(hit)
        res["pairs"] = {k: f"{sum(v)}/{len(v)}" for k, v in by.items()}
        res["pairs_acc"] = round(float(np.mean(by["all"])), 3)
        p = predict(m, tok, [M.norm(r["text"]) for r in bb])["score"][:, lv]
        res["brownbag_level_rho"] = round(float(spearmanr(p, [LEVEL[r["level"]] for r in bb]).correlation), 3)
        res["brownbag_n"] = len(bb)
        if speed:
            mc = m.float().cpu().eval()
            q = torch.ao.quantization.quantize_dynamic(mc, {torch.nn.Linear}, dtype=torch.qint8)
            torch.set_num_threads(4)
            for n in (40, 128):
                ids = torch.full((1, n), 1000); ids[0, 0] = 50281; ids[0, -1] = 50282
                with torch.no_grad():
                    for _ in range(3):
                        q(ids, torch.ones_like(ids))
                    t0 = time.perf_counter()
                    for _ in range(20):
                        q(ids, torch.ones_like(ids))
                res[f"ms_int8_4cpu_{n}tok"] = round((time.perf_counter() - t0) / 20 * 1000, 1)
            m.cuda()
        print(json.dumps(res), flush=True)
        with open(os.path.join(ROOT, "work", "multi", "extra.jsonl"), "a") as f:
            f.write(json.dumps(res) + "\n")


if __name__ == "__main__":
    main()

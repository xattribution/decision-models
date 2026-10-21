"""Train one score head on an Ettin encoder and test it on held-out real bullets.

  train_head.py --dim structure --arm synth|real|both [--base jhu-clsp/ettin-encoder-68m] [--epochs 3]

Data
  synth: pairs from synthetic ladders (synth/out/<set>_*.tsv) in groups the arbiter kept
         (synth/arb/<set>/keep.json); every pair the intended levels imply, minus pairs the arbiter
         put the other way round. Loss: logistic on the score difference.
  real:  round 4 key, even ids (train). Loss: MSE on the 0-5 score.
  test:  round 4 key, odd ids. Reported: Spearman rho, MAE after a linear fit on the train half.
"""
import argparse, csv, glob, json, os, random, sys, time

import torch
import torch.nn.functional as F
from scipy.stats import spearmanr
from transformers import AutoModel, AutoTokenizer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SET_OF = {"structure": "structure", "content": "content", "impact": "nmimpact"}
CONTENT = ["action", "impact", "result", "quantified", "scope", "credibility"]


def synth_pairs(setnames):
    """Pairs (better, worse, gap) from every kept group in each set, minus pairs the arbiter inverted."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from synth_arb import load, read_results
    pairs = []
    for setname in setnames.split(","):
        groups, _ = load(setname)
        d = os.path.join(ROOT, "synth", "arb", setname)
        keep = set(json.load(open(os.path.join(d, "keep.json"))))
        key, res = read_results(setname)
        for g in keep:
            if g not in res:
                continue
            order = [key[g][c] for c in res[g][0]]
            pos = {lv: i for i, lv in enumerate(order)}
            lv = sorted(groups[g])
            for a in lv:
                for b in lv:
                    if a > b and pos[a] < pos[b]:
                        pairs.append((groups[g][a], groups[g][b], a - b))
        print(f"set {setname}: {len(keep)} groups kept", flush=True)
    return pairs


def real_rows(dim, rnd="r4"):
    """r4: even ids train, odd ids test. r5: the bank items' own split (train / val)."""
    raw = json.load(open(os.path.join(ROOT, "panel", rnd, "items.json"), encoding="utf-8"))
    items = {str(x["id"]): x["text"] for x in raw}
    split = {str(x["id"]): x.get("split") for x in raw}
    tr, te = [], []
    for r in csv.DictReader(open(os.path.join(ROOT, "panel", rnd, "key.csv"), encoding="utf-8")):
        if r["id"] not in items:
            continue
        if dim == "content":
            vals = [r.get(c, "") for c in CONTENT]
            if "" in vals:
                continue
            v = sum(map(float, vals)) / len(vals)
        elif r.get(dim, "") == "":
            continue
        else:
            v = float(r[dim])
        row = (items[r["id"]], v, r["id"])
        if split.get(r["id"]):
            (tr if split[r["id"]] == "train" else te).append(row)
        else:
            digits = "".join(c for c in r["id"] if c.isdigit())
            (tr if digits and int(digits[-1]) % 2 == 0 else te).append(row)
    return tr, te


class Head(torch.nn.Module):
    def __init__(self, base):
        super().__init__()
        self.enc = AutoModel.from_pretrained(base)
        self.out = torch.nn.Linear(self.enc.config.hidden_size, 1)

    def forward(self, ids, mask):
        h = self.enc(input_ids=ids, attention_mask=mask).last_hidden_state
        m = mask.unsqueeze(-1).to(h.dtype)
        return self.out((h * m).sum(1) / m.sum(1)).squeeze(-1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", default="structure")
    ap.add_argument("--arm", default="synth", choices=["synth", "real", "both", "staged"])
    ap.add_argument("--sw", type=float, default=1.0, help="weight of the synthetic pair loss in arm both")
    ap.add_argument("--real-epochs", dest="real_epochs", type=int, default=30)
    ap.add_argument("--sets", default="", help="comma-separated synthetic sets (default: the dimension's ladder set)")
    ap.add_argument("--tag", default="", help="label added to the arm in results")
    ap.add_argument("--real", default="r4", help="panel round whose key supplies real labels (r4 or r5)")
    ap.add_argument("--base", default="jhu-clsp/ettin-encoder-68m")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--bs", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    random.seed(a.seed); torch.manual_seed(a.seed)
    dev = "cuda"
    tok = AutoTokenizer.from_pretrained(a.base)
    model = Head(a.base).to(dev)
    enc = lambda xs: tok(xs, padding=True, truncation=True, max_length=96, return_tensors="pt").to(dev)

    tr, te = real_rows(a.dim, a.real)
    te2 = real_rows(a.dim, "r4")[1] if a.real != "r4" else []   # the old 233-bullet test, for comparison
    pairs = synth_pairs(a.sets or SET_OF[a.dim]) if a.arm in ("synth", "both", "staged") else []
    print(f"arm={a.arm} base={a.base} synth_pairs={len(pairs)} real_train={len(tr)} test={len(te)}", flush=True)

    t0 = time.time()

    def phase(use_pairs, use_real, epochs, sw=1.0, tag=""):
        """One training phase with its own optimizer and warmup/decay schedule."""
        spe = max(len(pairs) // a.bs if use_pairs else 0, len(tr) // 16 if (use_real and not use_pairs) else 0, 1)
        opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=0.01)
        total = spe * epochs
        sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, s / max(1, total // 10)) * max(0.0, 1 - s / total))
        model.train()
        for ep in range(epochs):
            random.shuffle(pairs)
            for s in range(spe):
                loss = torch.zeros((), device=dev)
                with torch.autocast("cuda", dtype=torch.bfloat16):
                    if use_pairs:
                        b = pairs[s * a.bs:(s + 1) * a.bs] or random.sample(pairs, a.bs)
                        hi = enc([p[0] for p in b]); lo = enc([p[1] for p in b])
                        d = model(hi.input_ids, hi.attention_mask) - model(lo.input_ids, lo.attention_mask)
                        loss = loss + sw * F.softplus(-d.float()).mean()
                    if use_real:
                        b = random.sample(tr, min(16, len(tr)))
                        x = enc([r[0] for r in b])
                        y = torch.tensor([r[1] for r in b], device=dev)
                        loss = loss + F.mse_loss(model(x.input_ids, x.attention_mask).float(), y)
                opt.zero_grad(); loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step(); sched.step()
                if s % 200 == 0:
                    print(f"{tag} ep {ep} step {s}/{spe} loss {loss.item():.3f} {time.time() - t0:.0f}s", flush=True)

    if a.arm == "synth":
        phase(True, False, a.epochs, tag="synth")
    elif a.arm == "real":
        phase(False, True, a.real_epochs, tag="real")
    elif a.arm == "both":
        phase(True, True, a.epochs, sw=a.sw, tag="both")
    elif a.arm == "staged":
        phase(True, False, a.epochs, tag="stage1")
        phase(False, True, a.real_epochs, tag="stage2")

    model.eval()
    def score(rows):
        out = []
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
            for i in range(0, len(rows), 64):
                x = enc([r[0] for r in rows[i:i + 64]])
                out += model(x.input_ids, x.attention_mask).float().tolist()
        return out
    ptr, pte = score(tr), score(te)
    # linear map from raw score to the 0-5 scale, fit on the train half only
    import numpy as np
    A = np.vstack([ptr, np.ones(len(ptr))]).T
    k, c = np.linalg.lstsq(A, np.array([r[1] for r in tr]), rcond=None)[0]
    yte = np.array([r[1] for r in te]); fte = np.clip(k * np.array(pte) + c, 0, 5)
    rho = spearmanr(pte, yte).correlation
    mae = float(np.abs(fte - yte).mean())
    within1 = float((np.abs(fte - yte) <= 1).mean())
    arm = f"both@{a.sw:g}" if a.arm == "both" and a.sw != 1.0 else a.arm
    if a.tag:
        arm += f"+{a.tag}"
    res = {"dim": a.dim, "arm": arm, "base": a.base, "seed": a.seed, "rho": round(rho, 3), "mae": round(mae, 3),
           "within1": round(within1, 3), "n_test": len(te), "synth_pairs": len(pairs), "secs": round(time.time() - t0),
           "real": a.real, "n_train": len(tr)}
    if te2:
        p2 = score(te2)
        res["rho_r4"] = round(spearmanr(p2, [r[1] for r in te2]).correlation, 3)
    print(json.dumps(res), flush=True)
    os.makedirs(os.path.join(ROOT, "work", "heads"), exist_ok=True)
    with open(os.path.join(ROOT, "work", "heads", "results.jsonl"), "a") as f:
        f.write(json.dumps(res) + "\n")
    with open(os.path.join(ROOT, "work", "heads", f"pred_{a.dim}_{a.arm}_{a.seed}.tsv"), "w", encoding="utf-8") as f:
        for r, p in zip(te, fte):
            f.write(f"{r[2]}\t{r[1]}\t{p:.2f}\t{r[0]}\n")


if __name__ == "__main__":
    main()

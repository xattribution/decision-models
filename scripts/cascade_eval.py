"""The cascade on held-out scored items: small where its confidence clears the threshold, else medium.

  cascade_eval.py work/multi/s68.pt work/multi/m400.pt
"""
import json, os, sys
import numpy as np
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multi_data as M
from train_multi import load_model, predict
from transformers import AutoTokenizer

s, scfg = load_model(sys.argv[1]); m, _ = load_model(sys.argv[2])
tok = AutoTokenizer.from_pretrained(scfg["base"])
thr = scfg["cascade"]["threshold"]
sc = M.scored()
out = {"threshold": thr}
for split in ("val", "r4test"):
    rows = sc[split]; X = [r["text"] for r in rows]
    ps, pm = predict(s, tok, X), predict(m, tok, X)
    use = 1 / (1 + np.exp(-ps["conf"])) >= thr
    Y = np.array([r["scores"] for r in rows])
    g = np.array([r["gate"] for r in rows])
    res = {"answered_by_small": round(float(use.mean()), 3)}
    for name, p in (("small", ps), ("medium", pm), ("cascade", {k: np.where(use[:, None] if v.ndim > 1 else use, ps[k], v) for k, v in pm.items() if k in ("score", "gate")})):
        d = {}
        for k in ("structure", "impact", "overall"):
            j = M.SCORES.index(k); ok = ~np.isnan(Y[:, j])
            d[k] = round(float(spearmanr(p["score"][ok, j], Y[ok, j]).correlation), 3)
        cm = Y[:, M.CONTENT_IDX].mean(1); ok = ~np.isnan(cm)
        d["content"] = round(float(spearmanr(p["score"][ok][:, M.CONTENT_IDX].mean(1), cm[ok]).correlation), 3)
        okg = g >= 0
        d["gate_acc"] = round(float((p["gate"].argmax(1)[okg] == g[okg]).mean()), 3)
        res[name] = d
    out[split] = res
print(json.dumps(out))
with open(os.path.join(M.ROOT, "work", "multi", "extra.jsonl"), "a") as f:
    f.write(json.dumps({"cascade_eval": out}) + "\n")

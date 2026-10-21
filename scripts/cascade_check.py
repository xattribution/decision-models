"""How often the small model agrees with the medium one, under several definitions of agree, and how well
simple confidence signals pick the agreeing items. Uses the calibration slice of the bank (never distilled on).

  cascade_check.py work/multi/s68_nocal.pt work/multi/m400.pt
"""
import os, sys, json
import numpy as np, torch
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multi_data as M
from train_multi import load_model, predict, bank_texts
from transformers import AutoTokenizer

s, cfg = load_model(sys.argv[1]); t, _ = load_model(sys.argv[2])
tok = AutoTokenizer.from_pretrained(cfg["base"])
cal = [x for x, _ in bank_texts()[1]]
ps = predict(s, tok, cal); pt = predict(t, tok, cal)
import torch.nn.functional as F
d = np.abs(ps["score"][:, :12] - pt["score"][:, :12])
gs = ps["gate"].argmax(1) == pt["gate"].argmax(1)
ov = M.SCORES.index("overall")
crit = {
    "all11<=0.5": (d[:, :11].max(1) <= 0.5) & gs,
    "overall<=0.5": (d[:, ov] <= 0.5) & gs,
    "overall<=0.3": (d[:, ov] <= 0.3) & gs,
    "max11<=0.75": (d[:, :11].max(1) <= 0.75) & gs,
    "mean11<=0.25": (d[:, :11].mean(1) <= 0.25) & gs,
}
# signals the small model has on its own
pg = torch.softmax(torch.tensor(ps["gate"]), 1).numpy()
sig = {"gate_maxprob": pg.max(1), "neg_entropy": (pg * np.log(pg + 1e-9)).sum(1)}
pooled = []
with torch.no_grad():
    for i in range(0, len(cal), 64):
        x = tok(cal[i:i + 64], padding=True, truncation=True, max_length=128, return_tensors="pt").to("cuda")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            pooled.append(s(x.input_ids, x.attention_mask)["pooled"].float().cpu())
X = torch.cat(pooled).numpy()
n = len(cal); half = n // 2
out = {}
for name, y in crit.items():
    r = {"base": round(float(y.mean()), 3)}
    for sn, v in sig.items():
        r[sn] = round(float(roc_auc_score(y, v)), 3)
    lr = LogisticRegression(max_iter=2000, C=0.1).fit(X[:half], y[:half])
    c = lr.predict_proba(X[half:])[:, 1]
    r["probe_auc"] = round(float(roc_auc_score(y[half:], c)), 3)
    o = np.argsort(-c); cum = np.cumsum(y[half:][o]) / np.arange(1, n - half + 1)
    r["agree_at"] = {f: round(float(cum[int(f * (n - half)) - 1]), 3) for f in (0.3, 0.5, 0.7, 0.9)}
    out[name] = r
print(json.dumps(out, indent=1))
print("median abs diff per score:", dict(zip(M.SCORES, np.round(np.median(d, 0), 2).tolist())))

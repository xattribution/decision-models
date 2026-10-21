"""Reference points on the round 4 test half (odd ids) for one dimension.

  baselines.py DIM
  - surface rule: length band + has "--" + has ";" (fit on the even half)
  - single panel scorer vs the key (each of the 4 scorers' own score, ceiling for one judge)
"""
import csv, glob, json, os, sys
import numpy as np
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dim = sys.argv[1]
items = {str(x["id"]): x["text"] for x in json.load(open(os.path.join(ROOT, "panel", "r4", "items.json"), encoding="utf-8"))}
CONTENT = ["action", "impact", "result", "quantified", "scope", "credibility"]
cols_of = CONTENT if dim == "content" else [dim]
key = {}
for r in csv.DictReader(open(os.path.join(ROOT, "panel", "r4", "key.csv"), encoding="utf-8")):
    vals = [r.get(c, "") for c in cols_of]
    if r["id"] in items and "" not in vals and None not in vals:
        key[r["id"]] = sum(map(float, vals)) / len(vals)


def odd(i):
    d = "".join(c for c in i if c.isdigit())
    return not (d and int(d[-1]) % 2 == 0)


def feats(t):
    n = len(t)
    return [1, n <= 115, 115 < n <= 140, 140 < n <= 180, "--" in t, ";" in t, t.lstrip().startswith("-")]


tr = [i for i in key if not odd(i)]; te = [i for i in key if odd(i)]
X = np.array([feats(items[i]) for i in tr], float); y = np.array([key[i] for i in tr])
w = np.linalg.lstsq(X, y, rcond=None)[0]
pred = np.array([feats(items[i]) for i in te], float) @ w
yt = np.array([key[i] for i in te])
print(f"surface rule      rho {spearmanr(pred, yt).correlation:.3f}  within1 {(np.abs(np.clip(pred,0,5)-yt)<=1).mean():.3f}")

# panel scorers: panel/r4/out/*.tsv, header line names the columns
cols = None
per = {}
for f in sorted(glob.glob(os.path.join(ROOT, "panel", "r4", "out", "*.tsv"))):
    scorer = os.path.basename(f).split("_")[0]
    for line in open(f, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if p[0] == "id":
            cols = p; continue
        if cols and len(p) >= len(cols) - 1 and p[0] in key:
            try:
                per.setdefault(scorer, {})[p[0]] = sum(float(p[cols.index(c)]) for c in cols_of) / len(cols_of)
            except (ValueError, IndexError):
                pass
for s, m in sorted(per.items()):
    ids = [i for i in te if i in m]
    if len(ids) > 20:
        a = np.array([m[i] for i in ids]); b = np.array([key[i] for i in ids])
        print(f"panel scorer {s:4s} rho {spearmanr(a, b).correlation:.3f}  within1 {(np.abs(a-b)<=1).mean():.3f}  n={len(ids)}")
names = sorted(per)
rs = []
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        ids = [x for x in te if x in per[names[i]] and x in per[names[j]]]
        if len(ids) > 20:
            rs.append(spearmanr([per[names[i]][x] for x in ids], [per[names[j]][x] for x in ids]).correlation)
if rs:
    print(f"scorer vs scorer  mean rho {np.mean(rs):.3f} (fair ceiling for one judge)")

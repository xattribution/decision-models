"""How well do the round 4 grades order bullets the way Jared does, and which
weights would fit his picks best?

  analyze_pairs.py ROUND PAIRS_CSV
"""
import itertools, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
N = int(sys.argv[1])
P = ROOT / f"panel/r{N}"
k = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
items = {o["id"]: o for o in json.load(open(P / "items.json", encoding="utf-8"))}
pairs = pd.read_csv(sys.argv[2], dtype={"left": str, "right": str})
CONTENT = ["action", "impact", "result", "quantified", "scope", "credibility"]
k["content"] = k[CONTENT].mean(axis=1)
k["style"] = k[["readability", "tone", "clipping"]].mean(axis=1)
k["len"] = [len(items[i]["text"]) for i in k.index]
print(f"{len(pairs)} pairs picked: " + ", ".join(f"{a} {b}" for a, b in pairs["pick"].value_counts().items()))
dec = pairs[pairs["pick"] != "same"].copy()
dec["y"] = (dec["pick"] == "a").astype(int)  # 1 if the left bullet won


def agree(col, rows=dec):
    d = np.array([k.loc[a, col] - k.loc[b, col] for a, b in zip(rows.left, rows.right)])
    y = rows.y.to_numpy()
    hit = ((d > 0) & (y == 1)) | ((d < 0) & (y == 0))
    tie = d == 0
    return (hit.sum() + 0.5 * tie.sum()) / len(rows)


print("\nHow often each signal picks the same bullet you did (ties count half)")
print("signal          all   " + "  ".join(f"{kd[:12]:>12}" for kd in sorted(dec.kind.unique())))
for col in ["overall", "level", "content", "structure", "style", "readability", "credibility", "tone", "clipping", "len"]:
    row = f"{col:12} {agree(col):6.0%}"
    for kd in sorted(dec.kind.unique()):
        row += f"  {agree(col, dec[dec.kind == kd]):12.0%}"
    print(row)

# Fit weights: logistic regression on differences (Bradley-Terry), leave-one-out accuracy.
feats = ["structure", "content", "style", "level"]
X = np.array([[k.loc[a, f] - k.loc[b, f] for f in feats] for a, b in zip(dec.left, dec.right)])
y = dec.y.to_numpy()


def fit(X, y, lam=1.0, steps=3000, lr=0.05):
    w = np.zeros(X.shape[1])
    for _ in range(steps):
        p = 1 / (1 + np.exp(-X @ w))
        w -= lr * (X.T @ (p - y) / len(y) + lam * w / len(y))
    return w


loo = []
for i in range(len(y)):
    m = np.arange(len(y)) != i
    w = fit(X[m], y[m])
    loo.append(int((X[i] @ w > 0) == y[i]) if X[i] @ w != 0 else 0.5)
w = fit(X, y)
print(f"\nFitted weights from your picks (relative): " + ", ".join(f"{f} {v / np.abs(w).sum():.2f}" for f, v in zip(feats, w)))
print(f"leave-one-out accuracy with fitted weights: {np.mean(loo):.0%}  (current formula: {agree('overall'):.0%})")
print("\nPairs the current grade gets wrong")
for _, r in dec.iterrows():
    a, b = r.left, r.right
    win, lose = (a, b) if r.y == 1 else (b, a)
    if k.loc[win, "overall"] < k.loc[lose, "overall"]:
        print(f"  [{r.kind}] you picked {win} ({k.loc[win, 'overall']:.2f}) over {lose} ({k.loc[lose, 'overall']:.2f})")
        print(f"     won : {items[win]['text'][:150]}")
        print(f"     lost: {items[lose]['text'][:150]}")

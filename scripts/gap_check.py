"""Why does a dimension score lower on the val source? Scorer agreement and spread per source,
text shape per split, and where the model's errors fall.

  gap_check.py DIM [pred_file]
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.argv = [sys.argv[0], "x", "5"] + sys.argv[1:]
sys.path.insert(0, str(ROOT / "scripts"))
import panel4 as p

dim = sys.argv[3]
pred = sys.argv[4] if len(sys.argv) > 4 else None
df, items = p.load()
src = {i: o["src"] for i, o in items.items()}
w = df.pivot_table(index="id", columns="scorer", values=dim).dropna()
w["src"] = [src[i] for i in w.index]
print(f"{dim}: scorer s1 vs s2 by source")
for s, g in w.groupby("src"):
    if len(g) > 50:
        print(f"  {s:28s} n={len(g):5d} rho={spearmanr(g.s1, g.s2).correlation:.3f} "
              f"exact={(g.s1 == g.s2).mean():.0%} mean={g[['s1','s2']].values.mean():.2f} sd={g[['s1','s2']].values.std():.2f}")

k = pd.read_csv(ROOT / "panel/r5/key.csv", dtype={"id": str}).set_index("id")
k["text"] = [items[i]["text"] for i in k.index]
k["split"] = [items[i]["split"] for i in k.index]
t = k.text
k["dash"] = t.str.lstrip().str.startswith("-")
k["dd"] = t.str.contains("--")
k["semi"] = t.str.contains(";")
k["len"] = t.str.len()
print("\ntext shape by split")
print(k.groupby("split")[["dash", "dd", "semi", "len"]].mean().round(2))
print("\nkey", dim, "distribution by split")
print(k.groupby("split")[dim].value_counts(normalize=True).unstack().round(2))

if pred:
    pr = pd.read_csv(pred, sep="\t", header=None, names=["id", "y", "p", "text"], dtype={"id": str}).set_index("id")
    pr["err"] = pr.p - pr.y
    pr = pr.join(k[["dash", "dd", "semi", "len"]])
    print("\nmodel error on val by shape (mean signed error, mean abs error, n)")
    for c in ["dash", "dd", "semi"]:
        print(" ", c, pr.groupby(c).err.agg(["mean", lambda e: e.abs().mean(), "size"]).round(2).values.tolist())
    print("  by true score:", pr.groupby("y").err.agg(["mean", "size"]).round(2).to_dict("index"))
    worst = pr.reindex(pr.err.abs().sort_values(ascending=False).index).head(12)
    for i, r in worst.iterrows():
        print(f"  key {r.y:.0f} model {r.p:.1f} | {r.text[:150]}")

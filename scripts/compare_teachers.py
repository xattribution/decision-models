"""Compare the local teachers (and Fable's two passes, and Jared's hand scores
when present) with the panel's answer key, dimension by dimension.

  compare_teachers.py [ROUND, default 1]
"""
import csv, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1
P = ROOT / f"panel/r{N}"
DIMS7 = ["action", "impact", "result", "quantified", "scope", "readability", "guidance"]
DIMS8 = DIMS7 + ["level"]

key = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
key = key[key.junk == 0]
if len(sys.argv) > 2:  # even or odd: only that half of the rids
    key = key[key.index.astype(int) % 2 == (0 if sys.argv[2] == "even" else 1)]


def table(name, other, dims):
    j = key.join(other[dims], rsuffix="_o", how="inner")
    print(f"\n{name}: {len(j)} items (junk left out)")
    print("dimension     exact  within1  Spearman   bias")
    for d in dims:
        a, b = j[d], j[d + "_o"]
        print(f"{d:12}{np.mean(a == b):7.0%}{np.mean(abs(a - b) <= 1):9.0%}{a.corr(b, method='spearman'):10.2f}{(b - a).mean():+7.2f}")


for f in sorted((ROOT / "work").glob("labels-*.jsonl")):
    rows = [json.loads(l) for l in open(f, encoding="utf-8")]
    df = pd.DataFrame(rows)
    df["id"] = df.rid.astype(str)
    table(f.stem.replace("labels-", "teacher "), df.drop_duplicates("id").set_index("id"), DIMS7)

hand = ROOT / "scoring/scores.csv"
if hand.exists():
    h = pd.read_csv(hand, dtype={"id": str})
    h = h[h.get("skip").isna()] if "skip" in h else h
    for d in DIMS7:
        h[d] = h[d].round()
    table("Jared (sliders rounded)", h.set_index("id"), DIMS7)


def read_tsv(p):
    out = {}
    for ln in p.read_text(encoding="utf-8").splitlines()[1:]:
        f = ln.split("\t")
        if len(f) >= 9 and f[0].strip():
            out[f[0].strip()] = [int(x) if x.strip().isdigit() else np.nan for x in f[1:9]]
    return out


a, b = {}, {}
for k in range(1, 5):
    for src, dst in [(P / f"fable_{k}.tsv", a), (P / f"fable2_{k}.tsv", b)]:
        if src.exists():
            dst.update(read_tsv(src))
both = sorted(set(a) & set(b))
if both:
    A, B = np.array([a[i] for i in both], float), np.array([b[i] for i in both], float)
    print(f"\nFable pass 1 vs pass 2 on {len(both)} disputed items")
    print("dimension     exact  within1")
    for i, d in enumerate(DIMS8):
        print(f"{d:12}{np.nanmean(A[:, i] == B[:, i]):7.0%}{np.nanmean(abs(A[:, i] - B[:, i]) <= 1):9.0%}")

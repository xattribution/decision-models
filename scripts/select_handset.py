"""Step 2a: pick the ~500 items to score by hand, spread across type,
source and quality, and fence them off from training.

Marks those rows split=test in work/clean.parquet, moves training rows that
are close to any of them (MinHash Jaccard >= 0.5) out of training, and writes
scoring/items.json for the scoring page.
"""
import json, re
from pathlib import Path

import numpy as np
import pandas as pd
from datasketch import MinHash, MinHashLSH

ROOT = Path(__file__).resolve().parent.parent
WORK, OUT = ROOT / "work", ROOT / "scoring"
OUT.mkdir(exist_ok=True)
df = pd.read_parquet(WORK / "clean.parquet")
rng = np.random.default_rng(20261020)

QUOTA = {"classic_bullet": 190, "performance_statement": 80, "citation": 60, "push": 55, "stratification": 55}
FLAGS = [c for c in df.columns if c.startswith("f_")]
df["nflags"] = df[FLAGS].fillna(0).astype(int).sum(axis=1).clip(upper=2)


def pick(pool, n):
    """n rows spread evenly over sources, and within a source over flag counts."""
    chosen = []
    groups = {s: g.sample(frac=1, random_state=int(rng.integers(1 << 30))) for s, g in pool.groupby("source")}
    # interleave each source's rows by flag bucket so every source shows good and weak items
    queues = {}
    for s, g in groups.items():
        buckets = [list(b.index) for _, b in g.groupby("nflags")]
        order = []
        while any(buckets):
            for b in buckets:
                if b:
                    order.append(b.pop())
        queues[s] = order
    while len(chosen) < n and any(queues.values()):
        for s in sorted(queues, key=lambda s: len(queues[s])):
            if queues[s] and len(chosen) < n:
                chosen.append(queues[s].pop(0))
    return chosen


idx = pick(df[df.source == "ussf-bank"], 60)  # current USSF bullets, the forms the model serves first
for t, n in QUOTA.items():
    idx += pick(df[(df.type == t) & (df.source != "ussf-bank")], n)
df.loc[idx, "split"] = "test"


def mh(t):
    w = re.sub(r"[^a-z#]+", " ", re.sub(r"\d+(?:[.,]\d+)?", "#", t.lower())).split()
    m = MinHash(num_perm=64)
    for i in range(max(1, len(w) - 2)):
        m.update(" ".join(w[i:i + 3]).encode())
    return m


lsh = MinHashLSH(threshold=0.5, num_perm=64)
for i, t in zip(df.index[df.split != "test"], df.text[df.split != "test"]):
    lsh.insert(str(i), mh(t))
near = set()
for t in df.text[df.split == "test"]:
    near |= {int(k) for k in lsh.query(mh(t))}
near = [i for i in near if df.at[i, "split"] == "train"]
df.loc[near, "split"] = "near_test"
df.drop(columns=["nflags"]).to_parquet(WORK / "clean.parquet", index=False)

LIMIT = {"citation": 1350, "performance_statement": 350}


def fit(r):
    """fits_block from code: characters for narrative and citations, the
    two-line USSF width (~228 characters at 12 pt) for bullets."""
    if r.type in LIMIT:
        return 5 if len(r.text) <= LIMIT[r.type] else 0
    return 5 if len(r.text) <= 228 else 0


items = [{"id": int(r.rid), "text": r.text, "type": r.type, "source": r.source, "era": r.era, "fit": fit(r)}
         for r in df.loc[idx].sample(frac=1, random_state=7).itertuples()]
(OUT / "items.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
t = df.loc[idx]
print("test items", len(idx), "| moved from train as near copies:", len(near))
print(t.groupby(["type", "source"]).size().to_string())
print(df.split.value_counts().to_string())

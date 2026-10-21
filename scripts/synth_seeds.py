"""Pick seed bullets for synthetic ladders: real bullets from the training split
with real content (a number, the classic shape), spread across sources, plus
the Space Force training bullets. Never uses test or near-test rows.

  synth_seeds.py N PER_FILE
"""
import random, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
n, per = int(sys.argv[1]), int(sys.argv[2])
df = pd.read_parquet(ROOT / "work/clean.parquet")
df = df[(df.split == "train") & (df.type == "classic_bullet")]
t = df.text.str.strip()
ok = t.str.len().between(60, 180) & t.str.contains(r"\d") & (t.str.contains("--") | t.str.contains(";"))
pool = df[ok]
usf = pool[pool.source == "ussf-bank"]
rest = pool[pool.source != "ussf-bank"]
k = min(len(usf), n // 4)
seeds = pd.concat([usf.sample(k, random_state=1),
                   rest.groupby("source", group_keys=False).apply(lambda g: g.sample(min(len(g), (n - k) // rest.source.nunique() + 1), random_state=1))])
seeds = seeds.sample(frac=1, random_state=2).head(n)
out = ROOT / "synth/seeds"
out.mkdir(parents=True, exist_ok=True)
rows = [(int(r.rid), " ".join(r.text.split())) for r in seeds.itertuples()]
for i in range(0, len(rows), per):
    with open(out / f"seeds_{i // per + 1:03d}.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("seed\ttext\n")
        for rid, text in rows[i:i + per]:
            f.write(f"{rid}\t{text}\n")
print(len(rows), "seeds in", -(-len(rows) // per), "files;", seeds.source.value_counts().head(8).to_dict())

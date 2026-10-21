"""Pick real bullets for the panel to label (round R) and write panel/rR/items.json.

  bank_items.py R

All val bullets (the bigger test set), all Space Force train bullets, and a spread of
other train bullets, one per near-duplicate cluster. Skips removed rows, the test and
near-test splits, and anything earlier rounds already labeled.
"""
import json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = int(sys.argv[1])
QUOTA = {"github/justinthelaw/opera": 2000, "eprbullets.com": 2000, "eprbulletsafsc.com": 1000,
         "afeprbullets.com": 800, "airforcewriter.com": 382, "reddit.com": 29}

df = pd.read_parquet(ROOT / "work/clean.parquet")
df = df[(df.type == "classic_bullet") & (~df.removed.fillna(False).astype(bool))]
seen = set()
for r in range(1, R):
    f = ROOT / f"panel/r{r}/items.json"
    if f.exists():
        seen |= {str(o["id"]) for o in json.load(open(f, encoding="utf-8"))}
df = df[~df.rid.astype(str).isin(seen)]

val = df[df.split == "val"]
tr = df[df.split == "train"]
usf = tr[tr.source == "ussf-bank"]
rest = tr[tr.source != "ussf-bank"].drop_duplicates("cluster_id")
picks = [val, usf]
for src, n in QUOTA.items():
    g = rest[rest.source == src]
    picks.append(g.sample(min(n, len(g)), random_state=R))
sel = pd.concat(picks).drop_duplicates("rid")

items = [{"id": str(r.rid), "type": "bullet", "text": " ".join(str(r.text).split()), "src": r.source, "split": r.split}
         for r in sel.itertuples()]
out = ROOT / f"panel/r{R}"
out.mkdir(parents=True, exist_ok=True)
json.dump(items, open(out / "items.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(items), "items;", sel.split.value_counts().to_dict(), sel.source.value_counts().to_dict())

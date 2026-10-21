"""How round 1 and round 2 keys moved on the items Jared spot-checked."""
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D7 = ["action", "impact", "result", "quantified", "scope", "readability", "guidance"]
rv = pd.read_csv(ROOT / "scoring/review.csv", dtype={"id": str}).set_index("id")
k1 = pd.read_csv(ROOT / "panel/r1/key.csv", dtype={"id": str}).set_index("id")
k2 = pd.read_csv(ROOT / "panel/r2/key.csv", dtype={"id": str}).set_index("id")
items = {str(it["id"]): it for it in json.load(open(ROOT / "scoring/items.json", encoding="utf-8"))}
rows = []
for i, r in rv.iterrows():
    a, b = k1.loc[i], k2.loc[i]
    rows.append({"id": i, "vote": r.vote, "r1": a[D7].mean(), "r2": b[D7].mean(), "lev1": a.level, "lev2": b.level,
                 "junk1": a.junk, "junk2": b.junk, "note": r.note if isinstance(r.note, str) else ""})
df = pd.DataFrame(rows)
df["change"] = df.r2 - df.r1
print("Mean of the 7 scores, round 1 vs round 2")
for v, g in df.groupby("vote"):
    print(f"  {'thumbs up' if v == 1 else 'thumbs down'}: {len(g)} items, r1 {g.r1.mean():.2f} -> r2 {g.r2.mean():.2f} "
          f"(mean change {g.change.mean():+.2f}; {int((g.change < -0.2).sum())} down, {int((g.change > 0.2).sum())} up)")
print("\nThumbs-down items")
for _, r in df[df.vote == 0].iterrows():
    t = " ".join(items[r.id]["text"].split())[:90]
    print(f"  {r.id}: {r.r1:.1f} -> {r.r2:.1f}, level {int(r.lev1)} -> {int(r.lev2)} | {t}")

"""Quick test: does a gated, weighted overall score from the round 2 key
separate Jared's thumbs up from thumbs down on bullet-type items?"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BULLETS = {"classic_bullet", "push", "stratification"}
items = {str(it["id"]): it for it in json.load(open(ROOT / "scoring/items.json", encoding="utf-8"))}
k = pd.read_csv(ROOT / "panel/r2/key.csv", dtype={"id": str}).set_index("id")
votes = pd.concat([pd.read_csv(ROOT / f"scoring/{f}", dtype={"id": str}) for f in ["review.csv", "review_r2.csv"]])
votes = votes[votes.id.map(lambda i: items[i]["type"] in BULLETS)]


def overall(r):
    if r.junk or r.guidance == 0 or r.level == 0:          # gate: junk, banned, fluff or joke
        return 0.0
    content = np.mean([r.action, r.impact, r.result, r.quantified, r.scope])
    score = 0.7 * content + 0.3 * r.readability
    if r.readability <= 1:                                  # garbled or jargon soup
        score = min(score, 2)
    return score


k["overall"] = k.apply(overall, axis=1)
k["mean7"] = k[["action", "impact", "result", "quantified", "scope", "readability", "guidance"]].mean(axis=1)
v = votes.set_index("id").join(k[["overall", "mean7"]])
for col in ["mean7", "overall"]:
    up, dn = v[v.vote == 1][col], v[v.vote == 0][col]
    auc = np.mean([(a > b) + 0.5 * (a == b) for a in up for b in dn])
    print(f"{col:8} thumbs up mean {up.mean():.2f} ({len(up)}), thumbs down mean {dn.mean():.2f} ({len(dn)}), "
          f"chance a liked bullet outscores a disliked one {auc:.0%}")
print(v[v.vote == 0][["overall", "mean7"]].round(1).to_string())

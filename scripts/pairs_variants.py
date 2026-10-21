"""Try a few principled grade formulas against Jared's pair picks, without
rescoring anything. Reports accuracy on all decisive pairs and on each half
(odd and even pair numbers) so a variant that only fits one half shows up."""
import json, re, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "panel/r4"
k = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
items = {o["id"]: o for o in json.load(open(P / "items.json", encoding="utf-8"))}
pairs = pd.read_csv(ROOT / "scoring/pairs.csv", dtype={"left": str, "right": str})
dec = pairs[pairs["pick"] != "same"].reset_index(drop=True)
CONTENT = ["action", "impact", "result", "quantified", "scope", "credibility"]


def bullet_form(t):
    t = t.strip()
    return t.startswith("-") or ("--" in t) or (";" in t)


def grade(r, t, v):
    if r.gate != "pass":
        return 0.0
    s = r.structure
    if v["form"] and not bullet_form(t):
        s = min(s, 2)
    if len(t) > v["long"]:
        s = min(s, 2)
    c = np.mean([r[d] for d in CONTENT])
    style = np.mean([r[d] for d in v["style_dims"]]) if v["style_dims"] else 0
    g = v["ws"] * s + v["wc"] * c + v["wst"] * style + v["wl"] * 1.25 * r.level
    caps = []
    if s <= 1:
        caps.append(1.5)
    elif s == 2:
        caps.append(2.5)
    if r.readability <= v["read_cap_at"]:
        caps.append(1.5 + 0.75 * r.readability)
    return min([g] + caps)


V = {
    "current (round 4)": dict(form=False, long=230, ws=.2, wc=.5, wst=.15, wl=.15, style_dims=["readability", "tone", "clipping"], read_cap_at=2),
    "bullet-form rule": dict(form=True, long=230, ws=.2, wc=.5, wst=.15, wl=.15, style_dims=["readability", "tone", "clipping"], read_cap_at=2),
    "form + no clipping/readability in style": dict(form=True, long=230, ws=.2, wc=.55, wst=.1, wl=.15, style_dims=["tone"], read_cap_at=1),
    "form + structure-heavy": dict(form=True, long=230, ws=.35, wc=.45, wst=.1, wl=.1, style_dims=["tone"], read_cap_at=1),
    "form + structure-heavy + 180-char cap": dict(form=True, long=180, ws=.35, wc=.45, wst=.1, wl=.1, style_dims=["tone"], read_cap_at=1),
}
for name, v in V.items():
    g = {i: grade(k.loc[i], items[i]["text"], v) for i in k.index}
    hits = []
    for _, r in dec.iterrows():
        d = g[r.left] - g[r.right]
        hits.append(0.5 if d == 0 else float((d > 0) == (r["pick"] == "a")))
    h = np.array(hits)
    by = {kd: h[dec.kind == kd].mean() for kd in sorted(dec.kind.unique())}
    print(f"{name:42} all {h.mean():.0%} | odd {h[1::2].mean():.0%} even {h[0::2].mean():.0%} | "
          + " ".join(f"{kd[:6]} {x:.0%}" for kd, x in by.items()))
print("\nbullet form share by source:", pd.Series({i: bullet_form(items[i]['text']) for i in k.index})
      .groupby(lambda i: items[i]['src']).mean().round(2).to_dict())

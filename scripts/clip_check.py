"""How much of the clipping in bullets is on the approved list?

Counts, per bullet: approved acronyms, approved abbreviations, other acronyms
(all capitals, not on the list) and other clipped words (vowel-less words,
'd contractions, x/ forms) that aren't on the list.
"""
import json, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
T = json.load(open(ROOT / "data/approved_terms.json", encoding="utf-8"))
ACR = set(T["acronyms"])
ABB = {a.lower() for a in T["abbreviations"]}
COMMON = {"AB", "SrA", "SSgt", "TSgt", "MSgt", "SMSgt", "CMSgt", "Amn", "Spc1", "Spc2", "Spc3", "Spc4", "Sgt", "Lt", "Capt",
          "Maj", "Col", "Gen", "US", "USSF", "DoD"}
WORD = re.compile(r"[A-Za-z][A-Za-z0-9'’&/\-]*")
VOWEL = re.compile(r"[aeiouy]", re.I)


def classify(text):
    c = {"acr_ok": 0, "abb_ok": 0, "acr_other": 0, "clip_other": 0, "other_list": []}
    for w in WORD.findall(text.replace("’", "'")):
        w = w.strip("-/").rstrip("'s") if not w.endswith("/") else w
        if not w:
            continue
        base = w.split("/")[0] if "/" in w and not w.endswith("/") else w
        if w in ACR or base in ACR or w in COMMON:
            c["acr_ok"] += 1
        elif w.lower() in ABB or base.lower() in ABB or w.endswith("/") and w.lower() in ABB:
            c["abb_ok"] += 1
        elif re.fullmatch(r"[A-Z0-9&]{2,}s?", w):
            c["acr_other"] += 1
            c["other_list"].append(w)
        elif w.endswith("/") or re.search(r"[a-z]'d$", w) or (len(w) >= 2 and not VOWEL.search(w)):
            c["clip_other"] += 1
            c["other_list"].append(w)
    return c


items = json.load(open(ROOT / "panel/r3/items.json", encoding="utf-8"))
rows = []
for it in items:
    c = classify(it["text"])
    rows.append({"ussf": it["src"] == "ussf-bank", **{k: v for k, v in c.items() if k != "other_list"}, "others": c["other_list"]})
df = pd.DataFrame(rows)
print(df.groupby("ussf")[["acr_ok", "abb_ok", "acr_other", "clip_other"]].mean().round(2))
from collections import Counter
for flag in [True, False]:
    cnt = Counter(w for ws in df[df.ussf == flag].others for w in ws)
    print("\nmost common unlisted terms,", "Space Force" if flag else "others", ":", ", ".join(f"{w} {n}" for w, n in cnt.most_common(40)))

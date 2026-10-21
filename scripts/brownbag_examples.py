"""Pull the author-scored example bullets out of Brown Bag Lessons (AU Press,
2017, cleared for public release): each bullet, its overall performance
level and the 0-2 point score. Writes work/brownbag_scored.csv."""
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
lines = [l.replace("’", "'") for l in (ROOT / "work" / "txt" / "brown_bag_lessons.txt").read_text(encoding="utf-8").splitlines()]
NUM = {"zero": 0.0, "0": 0.0, "0.0": 0.0, "1/2": 0.5, "0.5": 0.5, "1": 1.0, "one": 1.0, "1.0": 1.0, "1 1/2": 1.5, "1.5": 1.5, "2": 2.0, "two": 2.0, "2.0": 2.0}
LEGEND = re.compile(r"^(Action|Accomplishment|Result|Impact|Leadership|Management|Supervisory|Membership|Fluff)\b")


def bullet_at(i):
    """The bullet starting at line i (a line beginning with an em dash), unwrapped."""
    text = lines[i].strip().lstrip("—").strip()
    j = i + 1
    while j < len(lines) and lines[j].strip() and not LEGEND.match(lines[j].strip()) and not lines[j].strip().startswith("—"):
        text += " " + lines[j].strip()
        j += 1
    return re.sub(r"\s+", " ", text)


rows = []
# Chapter 9: "Example 2: 1 1/2 points–Management" followed by the bullet.
head = re.compile(r"^Example (\d+): (Zero|1 1/2|1/2|\d(?:\.\d)?) points?\s*[—–-]\s*([A-Za-z]+)(.*)$")
for i, l in enumerate(lines):
    m = head.match(l.strip())
    if not m:
        continue
    for k in range(i + 1, min(i + 4, len(lines))):
        if lines[k].strip().startswith("—"):
            rows.append({"line": i + 1, "source": "ch9 practice", "text": bullet_at(k),
                         "points": NUM[m.group(2).lower()], "level": m.group(3).lower(), "note": m.group(4).strip()})
            break
# Chapter 8 traps: the bullet, its legend, then "1/2 point–fluff; ..."
trap = re.compile(r"^(Zero|1 1/2|1/2|\d(?:\.\d)?) points?\s*[—–-]", re.I)
for i, l in enumerate(lines):
    if l.strip().startswith("—") and any("Writing Traps" in x for x in lines[max(0, i - 400):i]) and not any("Perfect Practice Makes Perfect" == x.strip() for x in lines[max(0, i - 400):i]):
        for k in range(i + 1, min(i + 16, len(lines))):
            m = trap.match(lines[k].strip())
            if m:
                rows.append({"line": i + 1, "source": "ch8 traps", "text": bullet_at(i),
                             "points": NUM[m.group(1).lower().replace("zero", "zero")], "level": "", "note": lines[k].strip()[:120]})
                break
            if lines[k].strip().startswith("—"):
                break
# Chapter 7 practice package: "...text 1.5 pts."
pts = re.compile(r"^(.*?)\s*(\d\.\d) pts\.$")
for i, l in enumerate(lines):
    m = pts.match(l.strip())
    if m and len(m.group(1)) > 20:
        rows.append({"line": i + 1, "source": "ch7 package", "text": m.group(1).strip(), "points": float(m.group(2)), "level": "", "note": ""})
df = pd.DataFrame(rows).drop_duplicates("text")
df.to_csv(ROOT / "work" / "brownbag_scored.csv", index=False)
print(len(df), "scored bullets by source:", df.source.value_counts().to_dict())
print("points:", df.points.value_counts().sort_index().to_dict())
for r in df.sample(min(8, len(df)), random_state=1).itertuples():
    print(f"  {r.points} {r.level} | {r.text[:100]}")

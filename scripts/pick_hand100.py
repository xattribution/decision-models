"""Pick the 100 items Jared scores by hand: all 60 Space Force bullets and 40
public items spread over the types, then write scoring/hand.json. The full 500
stay in scoring/items.json for the teachers and the panel."""
import json, random, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SC = ROOT / "scoring"
QUOTA = {"classic_bullet": 17, "performance_statement": 7, "citation": 6, "push": 5, "stratification": 5}

items = json.loads((SC / "items.json").read_text(encoding="utf-8"))
sf = [it for it in items if it["source"] == "ussf-bank"]
rnd = random.Random(100)
pub = []
for t, n in QUOTA.items():
    pool = [it for it in items if it["source"] != "ussf-bank" and it["type"] == t]
    pub += rnd.sample(pool, n)
hand = sf + pub
rnd.shuffle(hand)
(SC / "hand.json").write_text(json.dumps(hand, ensure_ascii=False), encoding="utf-8")
print(len(sf), "Space Force +", len(pub), "public =", len(hand))

# Let the page generator take the item file as an argument.
page = ROOT / "scripts/make_scoring_page.py"
src = page.read_text(encoding="utf-8")
if "sys.argv" not in src:
    src = src.replace('(OUT / "items.json")', '(OUT / (sys.argv[1] if len(sys.argv) > 1 else "items.json"))', 1)
    src = re.sub(r"^import ", "import sys\nimport ", src, count=1, flags=re.M)
    page.write_text(src, encoding="utf-8")
    print("make_scoring_page.py now takes an item file")

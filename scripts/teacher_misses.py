"""Show where a teacher misses the panel key most, with the text and both notes.

  teacher_misses.py MODEL_FILE_STEM DIM [N]
"""
import json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
stem, dim = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 15
key = pd.read_csv(ROOT / "panel/r1/key.csv", dtype={"id": str}).set_index("id")
items = {str(it["id"]): it for it in json.load(open(ROOT / "scoring/items.json", encoding="utf-8"))}
lab = {str(r["rid"]): r for r in map(json.loads, open(ROOT / f"work/labels-{stem}.jsonl", encoding="utf-8"))}
reasons = {}
for f in sorted((ROOT / "panel/r1").glob("fable_*.tsv")):
    for ln in f.read_text(encoding="utf-8").splitlines()[1:]:
        p = ln.split("\t")
        if len(p) >= 12:
            reasons[p[0]] = p[11]
rows = []
for i, k in key[key.junk == 0].iterrows():
    if i in lab:
        rows.append((lab[i][dim] - k[dim], i, k[dim], lab[i][dim]))
rows.sort(key=lambda r: -abs(r[0]))
up = sum(1 for r in rows if r[0] > 1)
down = sum(1 for r in rows if r[0] < -1)
print(f"{dim}: teacher over key by 2+ on {up}, under by 2+ on {down}, of {len(rows)}")
for d, i, kv, tv in rows[:n]:
    it = items[i]
    print(f"\n[{i}] {it['type']} key {kv} teacher {tv}: {' '.join(it['text'].split())[:260]}")
    print(f"   teacher note: {lab[i].get('note', '')}")
    if i in reasons:
        print(f"   Fable: {reasons[i]}")

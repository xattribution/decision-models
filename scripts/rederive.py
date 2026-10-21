"""Recompute readability and guidance for v3 labels with the current derive()
rules, without asking the teacher again.

  rederive.py IN_STEM OUT_STEM     e.g. gemma3_27b-v3 gemma3_27b-v3b
"""
import json, sys
from pathlib import Path
from types import SimpleNamespace
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from label import derive  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
src, dst = sys.argv[1], sys.argv[2]
df = pd.read_parquet(ROOT / "work/clean.parquet", columns=["rid", "text", "type"]).set_index("rid")
n = 0
with open(ROOT / f"work/labels-{dst}.jsonl", "w", encoding="utf-8") as out:
    for line in open(ROOT / f"work/labels-{src}.jsonl", encoding="utf-8"):
        r = json.loads(line)
        if "error" not in r:
            row = df.loc[r["rid"]]
            r = derive(r, SimpleNamespace(text=row.text, type=row.type))
        out.write(json.dumps(r, ensure_ascii=False) + "\n")
        n += 1
print(n, "labels rederived")

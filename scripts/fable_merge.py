"""Merge two independent Fable passes (fableA_k, fableB_k) into fable_k.tsv:
where they differ, take the mean rounded down. Reports how often they agree.

  fable_merge.py ROUND
"""
import math, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from panel_agg import DIMS, read_tsv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / f"panel/r{sys.argv[1]}"
HEAD = "id\t" + "\t".join(DIMS) + "\ttype\tjunk\treason"
ex, w1, n = np.zeros(len(DIMS)), np.zeros(len(DIMS)), 0
for k in range(1, 5):
    a = {r["id"]: r for r in read_tsv(P / f"fableA_{k}.tsv", "A")}
    b = {r["id"]: r for r in read_tsv(P / f"fableB_{k}.tsv", "B")}
    lines = [HEAD]
    for i, ra in a.items():
        rb = b.get(i, ra)
        out = []
        for j, d in enumerate(DIMS):
            x, y = ra[d], rb[d]
            if x != x:
                x = y
            if y != y:
                y = x
            if i in b:
                ex[j] += x == y
                w1[j] += abs(x - y) <= 1
            out.append(str(int(math.floor((x + y) / 2))))
        n += i in b
        junk = int(ra["junk"] and rb["junk"])
        lines.append(f"{i}\t" + "\t".join(out) + f"\t{ra['type']}\t{junk}\t{ra['reason']}")
    (P / f"fable_{k}.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{n} items in both passes")
for j, d in enumerate(DIMS):
    print(f"  {d:12} same {ex[j] / n:.0%}  within 1 {w1[j] / n:.0%}")

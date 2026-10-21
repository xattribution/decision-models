"""Show groups where the arbiter ranked level LO above level HI.

  synth_show.py SET HI LO [N]
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synth_arb import load, SYN

setname, hi, lo = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
n = int(sys.argv[4]) if len(sys.argv) > 4 else 4
groups, _ = load(setname)
d = os.path.join(SYN, "arb", setname)
key = json.load(open(os.path.join(d, "key.json")))
shown = 0
for f in sorted(glob.glob(os.path.join(d, "r_*.tsv"))):
    for line in open(f, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) < 2 or p[0] not in key:
            continue
        lv = [key[p[0]][c] for c in p[1].strip()]
        if lo in lv and hi in lv and lv.index(lo) < lv.index(hi):
            print(p[0], "|", p[2] if len(p) > 2 else "")
            print(f"  {hi}: {groups[p[0]][hi]}")
            print(f"  {lo}: {groups[p[0]][lo]}")
            shown += 1
            if shown >= n:
                sys.exit()

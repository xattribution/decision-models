"""Check near-miss files: completeness, seed copied exactly, length and shorthand per level.

  nm_check.py SET [show N]
"""
import collections, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CL = re.compile(r"(?<![\w/])(f/|w/|w/o|mbrs?|msn|sq|wg|prsnl|trng|hrs|thru|tm|spt|mx|acct|lcls|dvcs?|\w+'d)(?![\w])", re.I)
setname = sys.argv[1]
show = int(sys.argv[3]) if len(sys.argv) > 3 else 0
seeds = {}
for f in glob.glob(os.path.join(ROOT, "synth", "seeds", "seeds_*.txt")):
    tag = os.path.basename(f)[6:9]
    for line in list(open(f, encoding="utf-8"))[1:]:
        p = line.rstrip("\n").split("\t")
        seeds[f"{tag}:{p[0]}"] = p[1]
g = collections.defaultdict(dict)
files = sorted(glob.glob(os.path.join(ROOT, "synth", "out", f"{setname}_*.tsv")))
for f in files:
    tag = os.path.basename(f)[len(setname) + 1:-4]
    for line in open(f, encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 3 and p[1].strip().isdigit():
            g[f"{tag}:{p[0]}"][int(p[1])] = p[2]
full = {k: v for k, v in g.items() if len(v) == 4}
exact = sum(v[2] == seeds.get(k) for k, v in full.items())
print(f"{len(files)} files: {[os.path.basename(f)[len(setname)+1:-4] for f in files]}")
print(f"groups {len(g)} complete {len(full)} seed-exact {exact}")
print("level  len  clips")
for L in (3, 2, 1, 0):
    xs = [v[L] for v in full.values()]
    print(f"{L:5d} {sum(map(len, xs)) / len(xs):5.0f} {sum(len(CL.findall(x)) for x in xs) / len(xs):6.2f}")
for k in list(full)[:show]:
    for L in (3, 2, 1, 0):
        print(k, L, full[k][L])

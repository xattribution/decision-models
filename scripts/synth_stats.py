"""Per-level stats for a synthetic ladder set: length, shorthand rate, separators.

  synth_stats.py SET tagA,tagB tagC,...   (groups of file tags to compare; default all files)
"""
import collections, glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CL = re.compile(r"(?<![\w/])(f/|w/|w/o|mbrs?|msn|sq|wg|prsnl|trng|hrs|thru|tm|spt|mx|acct|dvcs?|\w+'d)(?![\w])", re.I)


def load(setname, tags):
    g = collections.defaultdict(dict)
    for t in tags:
        for line in open(os.path.join(ROOT, "synth", "out", f"{setname}_{t}.tsv"), encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) == 3 and p[1].strip().isdigit():
                g[t + ":" + p[0]][int(p[1])] = p[2]
    return g


def main():
    setname = sys.argv[1]
    if len(sys.argv) > 2:
        sets = [a.split(",") for a in sys.argv[2:]]
    else:
        sets = [[os.path.basename(f)[len(setname) + 1:-4] for f in sorted(glob.glob(os.path.join(ROOT, "synth", "out", f"{setname}_*.tsv")))]]
    for tags in sets:
        g = load(setname, tags)
        full = [v for v in g.values() if len(v) == 6]
        print(f"files {tags[0]}..{tags[-1]}: {len(g)} groups, {len(full)} complete")
        print("  level  len  clips  has--  has;")
        for L in range(5, -1, -1):
            xs = [v[L] for v in full]
            ln = sum(map(len, xs)) / len(xs)
            c = sum(len(CL.findall(x)) for x in xs) / len(xs)
            print(f"  {L:5d} {ln:5.0f} {c:6.1f} {sum('--' in x for x in xs) / len(xs):6.0%} {sum(';' in x for x in xs) / len(xs):5.0%}")


if __name__ == "__main__":
    main()

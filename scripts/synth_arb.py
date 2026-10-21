"""Blind arbiter for synthetic groups (ladders of 6 levels, near-miss sets of 4, or any size).

  synth_arb.py batches SET [PER]   shuffle each complete group into letters, write synth/arb/SET/b_NNN.txt + key
  synth_arb.py score SET           read synth/arb/SET/r_*.tsv, compare with intended order, write keep list

A group is complete when it has every level the set uses (the levels seen across the set's files).
Kept: rank correlation >= KEEP_RHO for the group size and no flagged version.
"""
import glob, json, os, random, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYN = os.path.join(ROOT, "synth")
LET = "ABCDEFGH"
KEEP_RHO = {3: 0.99, 4: 0.79, 5: 0.89, 6: 0.94}  # 4: one adjacent swap allowed; 6: one adjacent swap


def load(setname):
    g = collections.defaultdict(dict)
    bad = 0
    for f in sorted(glob.glob(os.path.join(SYN, "out", f"{setname}_*.tsv"))):
        tag = os.path.basename(f)[len(setname) + 1:-4]
        for line in open(f, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) != 3 or not p[1].strip().isdigit():
                bad += line.strip() != ""
                continue
            g[f"{tag}:{p[0].strip()}"][int(p[1])] = p[2].strip()
    levels = set()
    for v in g.values():
        levels |= set(v)
    full = {k: v for k, v in g.items() if set(v) == levels}
    return full, bad


def batches(setname, per=60):
    groups, bad = load(setname)
    d = os.path.join(SYN, "arb", setname)
    os.makedirs(d, exist_ok=True)
    rng = random.Random(7)
    keys = sorted(groups)
    rng.shuffle(keys)
    key = {}
    for i in range(0, len(keys), per):
        n = i // per + 1
        with open(os.path.join(d, f"b_{n:03d}.txt"), "w", encoding="utf-8") as out:
            for k in keys[i:i + per]:
                lv = sorted(groups[k])
                rng.shuffle(lv)
                key[k] = {LET[j]: lv[j] for j in range(len(lv))}
                out.write(f"## {k}\n")
                for j in range(len(lv)):
                    out.write(f"{LET[j]}\t{groups[k][lv[j]]}\n")
    json.dump(key, open(os.path.join(d, "key.json"), "w"), indent=0)
    print(f"{len(groups)} complete groups ({bad} bad lines) in {(len(keys) + per - 1) // per} batches")


def spearman(order):
    # order: intended levels in arbiter order (best first)
    n = len(order)
    ideal = sorted(order, reverse=True)
    rank = {lv: i for i, lv in enumerate(ideal)}
    d2 = sum((i - rank[lv]) ** 2 for i, lv in enumerate(order))
    return 1 - 6 * d2 / (n * (n * n - 1))


def read_results(setname):
    d = os.path.join(SYN, "arb", setname)
    key = json.load(open(os.path.join(d, "key.json")))
    res = {}
    for f in glob.glob(os.path.join(d, "r_*.tsv")):
        for line in open(f, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) >= 2 and p[0] in key and sorted(p[1].strip()) == sorted(key[p[0]]):
                res[p[0]] = (p[1].strip(), p[2].strip() if len(p) > 2 else "")
    return key, res


def score(setname):
    d = os.path.join(SYN, "arb", setname)
    key, res = read_results(setname)
    rho, exact, keep = [], 0, []
    flips = collections.Counter()
    for k, (rk, note) in res.items():
        lv = [key[k][c] for c in rk]
        r = spearman(lv)
        rho.append(r)
        exact += lv == sorted(lv, reverse=True)
        for i in range(len(lv) - 1):
            if lv[i] < lv[i + 1]:
                flips[f"{lv[i + 1]}>{lv[i]}"] += 1
        if r >= KEEP_RHO.get(len(lv), 0.9) and not (note and note not in ("ok", "tie")):
            keep.append(k)
    n = len(res)
    print(f"{n}/{len(key)} ranked; exact order {exact} ({exact / max(n, 1):.0%}); "
          f"mean rho {sum(rho) / max(n, 1):.3f}; kept {len(keep)} ({len(keep) / max(n, 1):.0%})")
    print("most common inversions (arbiter put lower level above higher):", flips.most_common(8))
    flagged = [(k, v[1]) for k, v in res.items() if v[1] not in ("ok", "tie", "")]
    print("flags:", len(flagged))
    for k, note in flagged[:15]:
        print("  ", k, note)
    json.dump(sorted(keep), open(os.path.join(d, "keep.json"), "w"))


if __name__ == "__main__":
    cmd, setname = sys.argv[1], sys.argv[2]
    if cmd == "batches":
        batches(setname, int(sys.argv[3]) if len(sys.argv) > 3 else 60)
    elif cmd == "score":
        score(setname)

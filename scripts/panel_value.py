"""Which panel members earn their cost? Compares each scorer and each subset of
scorers with Fable's rulings and with the final key.

  panel_value.py [ROUND, default 1]
"""
import itertools, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from panel_agg import DIMS, load_round, read_tsv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1
P = ROOT / f"panel/r{N}"
HAIKU = ["s1", "s2", "s3", "s4", "s5", "s6"]
OPUS = ["s7", "s8"]

df = load_round(N)
OPUS = sorted({s for s in df.scorer.unique() if s not in HAIKU}, key=lambda s: int(s[1:]))
items = {str(it["id"]) for it in json.load(open(ROOT / "scoring/items.json", encoding="utf-8"))}
df = df[df.id.isin(items)].drop_duplicates(["scorer", "id"])
key = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
key = key[key.junk == 0]
fab = []
for f in sorted(P.glob("fable_*.tsv")):
    fab += read_tsv(f, "fable")
fab = pd.DataFrame(fab).set_index("id")
fab = fab[fab.index.isin(key.index)]
wide = {d: df.pivot(index="id", columns="scorer", values=d) for d in DIMS}


def agree(pred, ref):
    j = pd.concat([pred, ref], axis=1, join="inner").dropna()
    a, b = j.iloc[:, 0], j.iloc[:, 1]
    return np.mean(abs(a - b) < 0.5), np.mean(abs(a - b) <= 1)


print("Each scorer against Fable's rulings on disputed items (exact / within 1), mean over dimensions")
for s in HAIKU + OPUS:
    ex, w1 = zip(*[agree(wide[d][s], fab[d]) for d in DIMS])
    print(f"  {s} ({'Opus' if s in OPUS else 'Haiku'}): {np.mean(ex):.0%} / {np.mean(w1):.0%}")

print("\nSubsets of scorers, median rounded, against Fable on disputed items and the key on all items")
print("subset                      vs Fable exact  within1 | vs key exact")
subsets = {"1 Haiku (avg over 6)": [[s] for s in HAIKU], "3 Haiku (avg)": list(itertools.combinations(HAIKU, 3)),
           "6 Haiku": [HAIKU], "1 Opus (avg)": [[s] for s in OPUS],
           "2 Opus (avg)": [list(c) for c in itertools.combinations(OPUS, 2)], f"{len(OPUS)} Opus": [OPUS],
           "6 Haiku + 2 Opus (avg)": [HAIKU + list(c) for c in itertools.combinations(OPUS, 2)],
           f"6 Haiku + {len(OPUS)} Opus": [HAIKU + OPUS],
           f"3 Haiku + {len(OPUS)} Opus (avg)": [list(c) + OPUS for c in itertools.combinations(HAIKU, 3)]}
for name, groups in subsets.items():
    res = []
    for g in groups:
        g = list(g)
        fe, fw, ke = [], [], []
        for d in DIMS:
            m = wide[d][g].median(axis=1).round()
            e, w = agree(m, fab[d])
            fe.append(e); fw.append(w)
            ke.append(agree(m, key[d])[0])
        res.append((np.mean(fe), np.mean(fw), np.mean(ke)))
    r = np.mean(res, axis=0)
    print(f"  {name:26}{r[0]:14.0%}{r[1]:9.0%} |{r[2]:9.0%}")

print("\nHow far Fable moved the panel median on disputed items (mean absolute change), by dimension")
med = {d: wide[d].median(axis=1) for d in DIMS}
for d in DIMS:
    j = pd.concat([med[d], fab[d]], axis=1, join="inner").dropna()
    print(f"  {d:12}{np.mean(abs(j.iloc[:, 0] - j.iloc[:, 1])):.2f}  (Fable lower than median on {np.mean(j.iloc[:, 1] < j.iloc[:, 0] - 0.5):.0%})")

print("\nModel means across all items (higher = more lenient)")
for grp, ss in [("Haiku", HAIKU), ("Opus", OPUS)]:
    print(f"  {grp:6}" + "".join(f"{d[:4]} {np.nanmean(wide[d][ss].to_numpy()):.2f}  " for d in DIMS))
print("  Fable " + "".join(f"{d[:4]} {fab[d].mean():.2f}  " for d in DIMS) + " (disputed items only)")
print("  Key   " + "".join(f"{d[:4]} {key[d].mean():.2f}  " for d in DIMS))

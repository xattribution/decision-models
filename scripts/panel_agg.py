"""Combine the Claude panel's scores.

  panel_agg.py cal            scorers vs the Brown Bag author's points
  panel_agg.py round N        check round N, find disputes, write rN/disputes.txt
  panel_agg.py key N          merge round N with Fable's rulings into rN/key.csv
  panel_agg.py compare        round 1 key vs round 2 key
"""
import csv, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "panel"
DIMS = ["action", "impact", "result", "quantified", "scope", "readability", "guidance", "level"]
TYPE = {"classic_bullet": "bullet", "performance_statement": "narrative", "citation": "citation",
        "push": "push", "stratification": "stratification"}


def read_tsv(path, scorer):
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines()[1:]:
        f = ln.split("\t")
        if len(f) < 12 or not f[0].strip():
            continue
        r = {"id": f[0].strip(), "scorer": scorer}
        for d, v in zip(DIMS, f[1:9]):
            r[d] = int(v) if v.strip().isdigit() else np.nan
        r["type"], r["junk"], r["reason"] = f[9].strip(), f[10].strip() == "1", "\t".join(f[11:]).strip()
        rows.append(r)
    return rows


def spearman(a, b):
    return pd.Series(a).corr(pd.Series(b), method="spearman")


def cal(folder="cal"):
    bb = pd.read_csv(ROOT / "work/brownbag_scored.csv", encoding="utf-8")
    bb["id"] = "bb" + bb["line"].astype(str)
    rows = []
    for f in sorted((P / folder / "out").glob("*.tsv")):
        rows += read_tsv(f, f.stem)
    df = pd.DataFrame(rows).merge(bb[["id", "points"]], on="id")
    for s, g in df.groupby("scorer"):
        print(f"{s}: {len(g)} items, level vs author rho {spearman(g.level, g.points):.2f}, "
              f"within one level {np.mean(abs(g.level - g.points * 2) <= 1):.0%}, exact {np.mean(g.level == g.points * 2):.0%}")
    m = df.groupby("id").agg(level=("level", "mean"), points=("points", "first"))
    print(f"panel mean: rho {spearman(m.level, m.points):.2f}")
    print("author points vs panel level, by item:")
    for i, r in m.sort_values("points").iterrows():
        print(f"  {i}: author {r.points * 2:.0f}  panel {r.level:.1f}")


def load_round(n):
    rows = []
    for f in sorted((P / f"r{n}/out").glob("s*_b*.tsv")):
        rows += read_tsv(f, f.stem.split("_")[0])
    return pd.DataFrame(rows)


def trimmed_range(v):
    v = np.sort(v[~np.isnan(v)])
    if len(v) >= 5:
        v = v[1:-1]
    return v[-1] - v[0] if len(v) else 0


def round_(n):
    items = {str(it["id"]): it for it in json.load(open(ROOT / "scoring/items.json", encoding="utf-8"))}
    df = load_round(n)
    print(f"round {n}: {len(df)} score lines from {df.scorer.nunique()} scorers")
    for s, g in df.groupby("scorer"):
        miss = set(items) - set(g.id)
        extra = set(g.id) - set(items)
        dup = g.id.duplicated().sum()
        bad = g[DIMS].isna().any(axis=1).sum()
        if miss or extra or dup or bad:
            print(f"  {s}: missing {len(miss)}, unknown {len(extra)}, duplicate {dup}, bad values {bad}")
    df = df[df.id.isin(items)].drop_duplicates(["scorer", "id"])
    # each scorer against the median of the others
    print("  agreement with the rest of the panel (Spearman, by dimension):")
    print("  " + "scorer".ljust(8) + "".join(d[:7].rjust(8) for d in DIMS))
    for s in sorted(df.scorer.unique()):
        me = df[df.scorer == s].set_index("id")
        rest = df[df.scorer != s].groupby("id")[DIMS].median()
        j = me.join(rest, rsuffix="_r", how="inner")
        print("  " + s.ljust(8) + "".join(f"{spearman(j[d], j[d + '_r']):8.2f}" for d in DIMS))
    disputes = []
    for i, g in df.groupby("id"):
        hot = [d for d in DIMS if trimmed_range(g[d].to_numpy(float)) > 1]
        if hot:
            disputes.append((i, hot, g))
    print(f"  disputed items (trimmed range over 1 on a dimension): {len(disputes)}")
    counts = pd.Series([d for _, hot, _ in disputes for d in hot]).value_counts()
    print("  by dimension: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    parts = 4
    files = [open(P / f"r{n}/disputes_{k + 1}.txt", "w", encoding="utf-8", newline="\n") for k in range(parts)]
    for k, (i, hot, g) in enumerate(disputes):
        f = files[k % parts]
        if True:
            it = items[i]
            f.write(f"=== id {i} | bank type {TYPE[it['type']]}\n{' '.join(str(it['text']).split())}\n")
            f.write("disputed: " + ", ".join(hot) + "\n")
            for _, r in g.sort_values("scorer").iterrows():
                f.write(f"  {r.scorer}: " + " ".join(f"{d[:3]}={int(r[d]) if r[d] == r[d] else '?'}" for d in DIMS)
                        + f" junk={int(r.junk)} | {r.reason}\n")
            f.write("\n")
    for f in files:
        f.close()
    print(f"  wrote {parts} dispute files in {P / f'r{n}'}")


def key(n):
    df = load_round(n)
    items = {str(it["id"]): it for it in json.load(open(ROOT / "scoring/items.json", encoding="utf-8"))}
    df = df[df.id.isin(items)].drop_duplicates(["scorer", "id"])
    med = df.groupby("id")[DIMS].median()
    junk = df.groupby("id").junk.mean()
    typ = df.groupby("id").type.agg(lambda s: s.mode().iloc[0])
    out = med.round().astype(int)  # numpy rounds halves to even
    out["source"] = "median"
    for fp in sorted((P / f"r{n}").glob("fable_*.tsv")):
        for r in read_tsv(fp, "fable"):
            if r["id"] in out.index:
                for d in DIMS:
                    if r[d] == r[d]:
                        out.loc[r["id"], d] = int(r[d])
                out.loc[r["id"], "source"] = "fable"
                junk[r["id"]] = float(r["junk"])
                typ[r["id"]] = r["type"]
    out["junk"] = (junk >= 0.5).astype(int)
    out["type"] = typ
    for d in DIMS:
        out[d + "_mean"] = df.groupby("id")[d].mean().round(2)
    out.index.name = "id"
    out.to_csv(P / f"r{n}/key.csv")
    print(f"round {n} key: {len(out)} items, {int((out.source == 'fable').sum())} settled by Fable, {int(out.junk.sum())} junk")


def compare():
    a = pd.read_csv(P / "r1/key.csv", dtype={"id": str}).set_index("id")
    b = pd.read_csv(P / "r2/key.csv", dtype={"id": str}).set_index("id")
    j = a.join(b, rsuffix="_2", how="inner")
    print(f"{len(j)} items in both rounds")
    print("dimension     exact  within1  Spearman")
    for d in DIMS:
        print(f"{d:12}{np.mean(j[d] == j[d + '_2']):7.0%}{np.mean(abs(j[d] - j[d + '_2']) <= 1):9.0%}"
              f"{spearman(j[d], j[d + '_2']):10.2f}")
    print(f"junk agreement {np.mean(j.junk == j.junk_2):.0%}, type agreement {np.mean(j.type == j.type_2):.0%}")


if __name__ == "__main__":
    {"cal": lambda: cal(sys.argv[2] if len(sys.argv) > 2 else "cal"), "round": lambda: round_(int(sys.argv[2])), "key": lambda: key(int(sys.argv[2])),
     "compare": lambda: compare()}[sys.argv[1]]()

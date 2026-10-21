"""Round 3 and later: bullets only, gate + structure + content + style.

  panel3.py items R           build panel/rR/items.json and scorer batches (7 scorers, 4 batches)
  panel3.py round R           check scores, agreement, write dispute files
  panel3.py key R             merge with Fable rulings, compute the overall grade, write key.csv
  panel3.py check R           overall grade against Jared's votes, Brown Bag and afbulletsafe stars
"""
import json, random, re, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = int(sys.argv[2])
P = ROOT / f"panel/r{R}"
COLS = ["gate", "structure", "action", "impact", "result", "quantified", "scope", "credibility", "readability", "tone", "level"]
NUM = COLS[1:]
GATES = ["pass", "not_a_bullet", "incomplete", "nonsense", "banned"]
TYPE = {"classic_bullet": "bullet", "push": "push", "stratification": "strat"}
SCORERS, BATCHES = 7, 4

# Overall grade weights and caps; tune here, nothing needs relabeling.
W = {"structure": 0.2, "content": 0.6, "style": 0.2}
CONTENT = ["action", "impact", "result", "quantified", "scope", "credibility"]
STYLE = ["readability", "tone"]


def overall(r):
    if r["gate"] != "pass":
        return 0.0
    content = np.mean([r[d] for d in CONTENT])
    style = np.mean([r[d] for d in STYLE])
    g = W["structure"] * r["structure"] + W["content"] * content + W["style"] * style
    if r["structure"] <= 1:
        g = min(g, 1.5)
    elif r["structure"] == 2:
        g = min(g, 2.5)
    if r["readability"] <= 1 or r["tone"] <= 1 or r["credibility"] <= 1:
        g = min(g, 2.0)
    return round(g, 2)


def build_items():
    base = json.load(open(ROOT / "scoring/items.json", encoding="utf-8"))
    out = [{"id": str(it["id"]), "type": TYPE[it["type"]], "text": " ".join(it["text"].split()), "src": it["source"]}
           for it in base if it["type"] in TYPE]
    bb = pd.read_csv(ROOT / "work/brownbag_scored.csv", encoding="utf-8")
    out += [{"id": f"bb{r.line}", "type": "bullet", "text": " ".join(str(r.text).split()), "src": "brownbag",
             "points": float(r.points)} for r in bb.itertuples()]
    have = {o["text"] for o in out}
    rated = []
    for line in open(ROOT / "data_new/epr-bank/examples.jsonl", encoding="utf-8"):
        e = json.loads(line)
        m = re.search(r"avg rating (\d(?:\.\d)?)/5", e.get("critique") or "")
        t = " ".join(e["text"].split())
        if m and e["type"] in TYPE and t not in have:
            rated.append({"id": f"af{len(rated)}", "type": TYPE[e["type"]], "text": t, "src": "afbulletsafe-rated",
                          "stars": float(m.group(1))})
    random.Random(3).shuffle(rated)
    out += rated[:60]
    P.mkdir(parents=True, exist_ok=True)
    (P / "items.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    size = -(-len(out) // BATCHES)
    for s in range(1, SCORERS + 1):
        order = out[:]
        random.Random(1000 * R + s).shuffle(order)
        for b in range(BATCHES):
            with open(P / f"s{s}_b{b + 1}.txt", "w", encoding="utf-8", newline="\n") as f:
                f.write("id\tbank type\ttext\n")
                for it in order[b * size:(b + 1) * size]:
                    f.write(f"{it['id']}\t{it['type']}\t{it['text']}\n")
    (P / "out").mkdir(exist_ok=True)
    print(len(out), "items:", pd.Series([o["src"] for o in out]).value_counts().to_dict(), f"batch size {size}")


def read(path, who):
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines()[1:]:
        f = [x.strip() for x in ln.split("\t")]
        if len(f) < 13 or not f[0]:
            continue
        r = {"id": f[0], "scorer": who, "gate": f[1] if f[1] in GATES else "pass", "reason": " ".join(f[12:])}
        for c, v in zip(NUM, f[2:12]):
            r[c] = int(v) if v.isdigit() else np.nan
        rows.append(r)
    return rows


def load():
    rows = []
    for f in sorted((P / "out").glob("s*_b*.tsv")):
        rows += read(f, f.stem.split("_")[0])
    items = {o["id"]: o for o in json.load(open(P / "items.json", encoding="utf-8"))}
    df = pd.DataFrame(rows)
    return df[df.id.isin(items)].drop_duplicates(["scorer", "id"]), items


def trimmed_range(v):
    v = np.sort(v[~np.isnan(v)])
    if len(v) >= 5:
        v = v[1:-1]
    return v[-1] - v[0] if len(v) else 0


def round_():
    df, items = load()
    print(f"{len(df)} score lines, {df.scorer.nunique()} scorers")
    for s, g in df.groupby("scorer"):
        miss = len(set(items) - set(g.id))
        if miss:
            print(f"  {s} missing {miss}")
    disputes = []
    for i, g in df.groupby("id"):
        gv = g.gate.value_counts()
        hot = [c for c in NUM if trimmed_range(g[c].to_numpy(float)) > 1]
        if gv.iloc[0] / len(g) < 0.75:
            hot = ["gate"] + hot
        if hot:
            disputes.append((i, hot, g))
    print(f"disputed: {len(disputes)} of {len(items)}")
    files = [open(P / f"disputes_{k + 1}.txt", "w", encoding="utf-8", newline="\n") for k in range(4)]
    for k, (i, hot, g) in enumerate(disputes):
        f = files[k % 4]
        f.write(f"=== id {i} | bank type {items[i]['type']}\n{items[i]['text']}\ndisputed: {', '.join(hot)}\n")
        for _, r in g.sort_values("scorer").iterrows():
            f.write(f"  {r.scorer}: gate={r.gate} " + " ".join(f"{c[:4]}={'?' if r[c] != r[c] else int(r[c])}" for c in NUM)
                    + f" | {r.reason}\n")
        f.write("\n")
    for f in files:
        f.close()


def key():
    df, items = load()
    out = df.groupby("id")[NUM].median().round()
    out["gate"] = df.groupby("id").gate.agg(lambda s: s.value_counts().index[0])
    out["how"] = "median"
    for fp in sorted(P.glob("fable_*.tsv")):
        for r in read(fp, "fable"):
            if r["id"] in out.index:
                for c in NUM:
                    if r[c] == r[c]:
                        out.loc[r["id"], c] = r[c]
                out.loc[r["id"], "gate"] = r["gate"]
                out.loc[r["id"], "how"] = "fable"
    out["overall"] = [overall(r) for _, r in out.iterrows()]
    out.index.name = "id"
    out.to_csv(P / "key.csv")
    print(f"key: {len(out)} items, {int((out.how == 'fable').sum())} settled by Fable")
    print("gates:", out.gate.value_counts().to_dict())
    print("overall grade, mean by gate pass:", round(out[out.gate == "pass"].overall.mean(), 2))


def check():
    k = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
    items = {o["id"]: o for o in json.load(open(P / "items.json", encoding="utf-8"))}
    sp = lambda a, b: pd.Series(list(a)).corr(pd.Series(list(b)), method="spearman")
    bb = [(items[i]["points"], k.loc[i, "overall"], k.loc[i, "level"]) for i in k.index if i.startswith("bb")]
    print(f"Brown Bag author points vs overall rho {sp([x[0] for x in bb], [x[1] for x in bb]):.2f}, "
          f"vs level rho {sp([x[0] for x in bb], [x[2] for x in bb]):.2f} ({len(bb)} bullets)")
    af = [(items[i]["stars"], k.loc[i, "overall"]) for i in k.index if i.startswith("af")]
    print(f"afbulletsafe reader stars vs overall rho {sp([x[0] for x in af], [x[1] for x in af]):.2f} ({len(af)} bullets)")
    for f in ["review.csv", "review_r2.csv"]:
        v = pd.read_csv(ROOT / f"scoring/{f}", dtype={"id": str})
        v = v[v.id.isin(k.index)]
        print(f"\n{f}: {len(v)} bullets you voted on")
        for _, r in v.iterrows():
            x = k.loc[r.id]
            note = r.note if isinstance(r.note, str) else ""
            print(f"  {'UP  ' if r.vote == 1 else 'DOWN'} {r.id:>9} overall {x.overall:.1f} gate {x.gate:12} "
                  f"struct {int(x.structure)} cred {int(x.credibility)} read {int(x.readability)} tone {int(x.tone)} | "
                  f"{items[r.id]['text'][:60]} | {note[:50]}")


def packet():
    """A plain-text packet for reviewer agents: no code needed to read it."""
    import contextlib, io
    k = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
    items = {o["id"]: o for o in json.load(open(P / "items.json", encoding="utf-8"))}
    df, _ = load()
    reasons = df[df.scorer.isin(["s4", "s5"])].groupby("id").reason.first()
    for fp in sorted(P.glob("fable_*.tsv")):
        for r in read(fp, "fable"):
            reasons[r["id"]] = "Fable: " + r["reason"]
    k["src"] = [items[i]["src"] for i in k.index]
    k["text"] = [items[i]["text"] for i in k.index]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(f"# Round {R} review packet\n")
        print("Overall grade = 0 if the gate fails; else 0.2 structure + 0.6 mean(action, impact, result, quantified, "
              "scope, credibility) + 0.2 mean(readability, tone), capped at 1.5 if structure <= 1, 2.5 if structure = 2, "
              "2.0 if readability, tone or credibility <= 1.\n")
        print("## Gate results by source\n")
        print(pd.crosstab(k.src, k.gate).to_string(), "\n")
        print("## Overall grade by source (passing bullets)\n")
        print(k[k.gate == "pass"].groupby("src").overall.describe()[["count", "mean", "25%", "50%", "75%"]].round(2).to_string(), "\n")
        print("## External checks\n")
        check()
        def show(rows, title):
            print(f"\n## {title}\n")
            for i, x in rows.iterrows():
                print(f"- [{i}] {x.src} | overall {x.overall:.1f} gate {x.gate} | S{int(x.structure)} A{int(x.action)} "
                      f"I{int(x.impact)} R{int(x.result)} Q{int(x.quantified)} Sc{int(x.scope)} C{int(x.credibility)} "
                      f"Rd{int(x.readability)} T{int(x.tone)} L{int(x.level)} | {x.text} | {reasons.get(i, '')}")
        p = k[k.gate == "pass"]
        show(p.sort_values("overall", ascending=False).head(25), "25 highest-graded bullets")
        show(p.sort_values("overall").head(25), "25 lowest-graded bullets that passed the gate")
        show(k[k.gate != "pass"].sample(min(25, int((k.gate != "pass").sum())), random_state=1), "25 bullets that failed the gate")
        show(k[k.src == "ussf-bank"].sample(20, random_state=2), "20 Space Force bullets")
    (P / "packet.md").write_text(buf.getvalue(), encoding="utf-8")
    print("wrote", P / "packet.md", len(buf.getvalue()), "chars")


if __name__ == "__main__":
    {"items": build_items, "round": round_, "key": key, "check": check, "packet": packet}[sys.argv[1]]()

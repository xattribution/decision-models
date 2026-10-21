"""Round 4 and later: rubric4 (clipping split from readability), 4 Opus scorers,
disputes decided on the overall grade, Fable rules only on the split parts.

  panel4.py items R SRC       copy items from round SRC, write batches for 4 scorers
  panel4.py round R           check scores, write dispute files
  panel4.py key R             merge Fable rulings, compute the overall grade, write key.csv
  panel4.py check R           checks against Brown Bag, Jared's votes and the reviewers' tests
  panel4.py packet R          plain-text packet for reviewer agents
"""
import contextlib, io, json, random, shutil, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = int(sys.argv[2])
P = ROOT / f"panel/r{R}"
NUM = ["structure", "action", "impact", "result", "quantified", "scope", "credibility", "readability", "clipping", "tone", "level"]
GATES = ["pass", "not_a_bullet", "incomplete", "nonsense", "banned"]
SCORERS, BATCHES = 4, 4
_cfg = P / "config.json"   # a round can set {"scorers": 2, "batch_size": 120}
if _cfg.exists():
    _c = json.load(open(_cfg))
    SCORERS = _c.get("scorers", SCORERS)
    if "batch_size" in _c and (P / "items.json").exists():
        BATCHES = -(-len(json.load(open(P / "items.json", encoding="utf-8"))) // _c["batch_size"])
CONTENT = ["action", "impact", "result", "quantified", "scope", "credibility"]
# Fitted to Jared's 100 pair picks (21 Oct 26): clipping and readability don't
# add to the grade (he prefers dense, real-bullet lines); readability only caps
# garble. Tone stays as the style term.
STYLE = ["tone"]
W = {"structure": 0.2, "content": 0.55, "style": 0.1, "level": 0.15}
LONG = 180  # characters: a bullet this long can't fit the form's line
READ_CAP_AT = 1


def half_up(x):
    return np.floor(np.asarray(x, float) + 0.5)


def finalize(r, text_len):
    """Code rules on top of the scores: gate fixes, length, then the grade."""
    r = dict(r)
    if r["gate"] == "pass" and r["readability"] == 0:
        r["gate"] = "nonsense"
    if r["gate"] == "pass" and r["action"] <= 1 and r["structure"] <= 1:
        r["gate"] = "incomplete"
    if text_len > LONG:
        r["structure"] = min(r["structure"], 2)
    if r["gate"] != "pass":
        r["overall"] = 0.0
        return r
    content = np.mean([r[d] for d in CONTENT])
    style = np.mean([r[d] for d in STYLE])
    g = (W["structure"] * r["structure"] + W["content"] * content + W["style"] * style
         + W["level"] * 1.25 * r["level"])
    caps = []
    if r["structure"] <= 1:
        caps.append(1.5)
    elif r["structure"] == 2:
        caps.append(2.5)
    if r["readability"] <= READ_CAP_AT:
        caps.append(1.5 + 0.75 * r["readability"])
    for d in ("credibility", "tone"):
        if r[d] <= 1 and g > 2.0:          # soft cap: keep a quarter of the excess
            g = 2.0 + 0.25 * (g - 2.0)
    if caps:
        g = min(g, min(caps))
    r["overall"] = round(float(g), 2)
    return r


def build_items(src):
    P.mkdir(parents=True, exist_ok=True)
    if src != R:   # src == R: items.json is already in place (bank_items.py)
        shutil.copy(ROOT / f"panel/r{src}/items.json", P / "items.json")
    out = json.load(open(P / "items.json", encoding="utf-8"))
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
    print(len(out), "items, batch size", size)


BAD = []


def read(path, who):
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines()[1:]:
        f = [x.strip() for x in ln.split("\t")]
        if len(f) < 14 or not f[0]:
            if ln.strip():
                BAD.append((who, "short line", ln[:60]))
            continue
        gate = f[1].lower().replace(" ", "_")
        if gate not in GATES:
            BAD.append((who, f"unknown gate {f[1]!r}", f[0]))
            gate = None
        r = {"id": f[0], "scorer": who, "gate": gate, "reason": " ".join(f[13:])}
        for c, v in zip(NUM, f[2:13]):
            top = 4 if c == "level" else 5
            r[c] = int(v) if v.isdigit() and int(v) <= top else np.nan
            if r[c] != r[c]:
                BAD.append((who, f"bad {c} {v!r}", f[0]))
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
    v = np.sort(np.asarray(v, float))
    v = v[~np.isnan(v)]
    if len(v) >= 5:
        v = v[1:-1]
    return v[-1] - v[0] if len(v) else 0


def spread(g, items):
    """Which parts of one item the scorers split on."""
    n = len(items[g.id.iloc[0]]["text"])
    gates = g.gate.dropna()
    split_gate = len(gates) and gates.value_counts().iloc[0] / len(gates) < 0.75
    per = [finalize(r, n)["overall"] for r in g[NUM + ["gate"]].to_dict("records") if r["gate"] and not any(r[c] != r[c] for c in NUM)]
    split_overall = trimmed_range(per) > 0.75
    hot = [c for c in NUM if trimmed_range(g[c]) > 1] if split_overall else []
    return bool(split_gate), hot


def round_():
    df, items = load()
    print(f"{len(df)} score lines, {df.scorer.nunique()} scorers")
    for s, g in df.groupby("scorer"):
        miss = len(set(items) - set(g.id))
        if miss:
            print(f"  {s} missing {miss}")
    if BAD:
        print(f"  {len(BAD)} bad values, e.g. {BAD[:3]}")
    disputes = []
    for i, g in df.groupby("id"):
        sg, hot = spread(g, items)
        if sg or hot:
            disputes.append((i, (["gate"] if sg else []) + hot, g))
    print(f"disputed: {len(disputes)} of {len(items)}")
    files = [open(P / f"disputes_{k + 1}.txt", "w", encoding="utf-8", newline="\n") for k in range(4)]
    for k, (i, hot, g) in enumerate(disputes):
        f = files[k % 4]
        f.write(f"=== id {i} | bank type {items[i]['type']} | {len(items[i]['text'])} characters\n{items[i]['text']}\n"
                f"rule on: {', '.join(hot)}\n")
        for _, r in g.sort_values("scorer").iterrows():
            f.write(f"  {r.scorer}: gate={r.gate} " + " ".join(f"{c[:4]}={'?' if r[c] != r[c] else int(r[c])}" for c in NUM)
                    + f" | {r.reason}\n")
        f.write("\n")
    for f in files:
        f.close()


def key():
    df, items = load()
    med = df.groupby("id")[NUM].median().apply(half_up)
    gate = df.dropna(subset=["gate"]).groupby("id").gate.agg(lambda s: s.value_counts().index[0])
    out = med.copy()
    out["gate"] = gate
    out["how"] = "median"
    want = {}
    for i, g in df.groupby("id"):
        sg, hot = spread(g, items)
        if sg or hot:
            want[i] = (["gate"] if sg else []) + hot
    ruled = set()
    for fp in sorted(P.glob("fable_*.tsv")):
        for r in read(fp, "fable"):
            i = r["id"]
            if i not in want or i in ruled:
                continue
            ruled.add(i)
            for c in want[i]:
                if c == "gate":
                    if r["gate"]:
                        out.loc[i, "gate"] = r["gate"]
                elif r[c] == r[c]:
                    out.loc[i, c] = r[c]
            out.loc[i, "how"] = "fable"
    missing = set(want) - ruled
    if missing:
        print(f"WARNING: {len(missing)} disputes have no ruling yet")
    if out[NUM].isna().any().any():
        raise SystemExit(f"missing scores for {out[out[NUM].isna().any(axis=1)].index.tolist()[:5]}")
    rows = [finalize(r, len(items[i]["text"])) | {"id": i, "how": r["how"]}
            for i, r in zip(out.index, out.to_dict("records"))]
    out = pd.DataFrame(rows).set_index("id")
    out.to_csv(P / "key.csv")
    print(f"key: {len(out)} items, {len(ruled)} with Fable rulings")
    print("gates:", out.gate.value_counts().to_dict())
    print("mean overall of passing bullets:", round(out[out.gate == "pass"].overall.mean(), 2))
    if BAD:
        print(f"{len(BAD)} bad values in the inputs")


def check():
    k = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
    items = {o["id"]: o for o in json.load(open(P / "items.json", encoding="utf-8"))}
    k["src"] = [items[i]["src"] for i in k.index]
    sp = lambda a, b: pd.Series(list(a)).corr(pd.Series(list(b)), method="spearman")
    bb = k[k.index.str.startswith("bb")]
    pts = [items[i]["points"] for i in bb.index]
    print(f"Brown Bag author points: vs overall rho {sp(pts, bb.overall):.2f}, vs level rho {sp(pts, bb.level):.2f}")
    p = k[k.gate == "pass"]
    usf = p[p.src == "ussf-bank"].overall
    print(f"Space Force passing bullets: mean {usf.mean():.2f}, 25th percentile {usf.quantile(.25):.2f}, "
          f"at exactly 2.0: {int((usf == 2.0).sum())}")
    print("mean overall by source:", p.groupby("src").overall.mean().round(2).sort_values(ascending=False).to_dict())
    tests = {"10000484": "3.3-3.8", "57830": "< 2.6", "29540": "< 2.8", "54854": "fail", "47876": "fail", "31422": "fail",
             "14395": "fail", "50375": "low or fail", "14027": "lower than r3 3.4"}
    print("\nreviewers' tests:")
    for i, want in tests.items():
        if i in k.index:
            print(f"  {i}: gate {k.loc[i, 'gate']}, overall {k.loc[i, 'overall']:.2f} (wanted {want})")
    for f in ["review.csv", "review_r2.csv"]:
        v = pd.read_csv(ROOT / f"scoring/{f}", dtype={"id": str})
        v = v[v.id.isin(k.index) & (v.vote == 0)]
        for _, r in v.iterrows():
            print(f"  your thumbs-down {r.id}: gate {k.loc[r.id, 'gate']}, overall {k.loc[r.id, 'overall']:.2f} | "
                  f"{(r.note if isinstance(r.note, str) else '')[:60]}")


def packet():
    k = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
    items = {o["id"]: o for o in json.load(open(P / "items.json", encoding="utf-8"))}
    df, _ = load()
    reasons = df[df.scorer.isin(["s1", "s2"])].groupby("id").reason.first()
    for fp in sorted(P.glob("fable_*.tsv")):
        for r in read(fp, "fable"):
            reasons[r["id"]] = "Fable: " + r["reason"]
    k["src"] = [items[i]["src"] for i in k.index]
    k["type"] = [items[i]["type"] for i in k.index]
    k["text"] = [items[i]["text"] for i in k.index]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print(f"# Round {R} review packet\n")
        print("Overall = 0 if the gate fails; else 0.2 structure + 0.5 mean(action, impact, result, quantified, scope, "
              "credibility) + 0.15 mean(readability, tone, clipping) + 0.15 x 1.25 x level. Caps: structure <= 1 at 1.5, "
              "structure 2 at 2.5, readability <= 2 at 1.5 + 0.75 x readability; credibility or tone <= 1 keeps a quarter "
              "of anything over 2.0. Code rules: readability 0 fails as nonsense; action <= 1 and structure <= 1 fails as "
              f"incomplete; over {LONG} characters caps structure at 2.\n")
        print("## Gate results by source\n")
        print(pd.crosstab(k.src, k.gate).to_string(), "\n")
        print("## Overall grade by source (passing bullets)\n")
        print(k[k.gate == "pass"].groupby("src").overall.describe()[["count", "mean", "25%", "50%", "75%"]].round(2).to_string(), "\n")
        print("## Checks\n")
        check()

        def show(rows, title):
            print(f"\n## {title}\n")
            for i, x in rows.iterrows():
                print(f"- [{i}] {x.src} ({x.type}) | overall {x.overall:.2f} gate {x.gate} | S{int(x.structure)} "
                      f"A{int(x.action)} I{int(x.impact)} R{int(x.result)} Q{int(x.quantified)} Sc{int(x.scope)} "
                      f"C{int(x.credibility)} Rd{int(x.readability)} Cl{int(x.clipping)} T{int(x.tone)} L{int(x.level)} | "
                      f"{x.text} | {reasons.get(i, '')}")
        p = k[k.gate == "pass"]
        show(p.sort_values("overall", ascending=False).head(25), "25 highest-graded bullets")
        show(p.sort_values("overall").head(25), "25 lowest-graded bullets that passed the gate")
        show(k[k.gate != "pass"].sample(min(25, int((k.gate != "pass").sum())), random_state=1), "25 bullets that failed the gate")
        show(k[k.src == "ussf-bank"].sample(20, random_state=2), "20 Space Force bullets")
    (P / "packet.md").write_text(buf.getvalue(), encoding="utf-8")
    print("wrote", P / "packet.md")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "items":
        build_items(int(sys.argv[3]))
    else:
        {"round": round_, "key": key, "check": check, "packet": packet}[cmd]()

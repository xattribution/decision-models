"""Data for the multi-head decision model. Every text goes through norm() first, the same as the app must do.

Rows
  scored  (text, scores[12] with NaN for missing, gate index, id, src)       r5 key (train/val) + r4 key (even ids train, odd test)
  typed   (text, type index)                                                 bank by split, plus Opera's bullet->narrative pairs
  spans   (text, {field: [[a, b], ...]})                                     panel/spans/spans.jsonl
  same    (text a, text b)                                                   statements that say the same thing
"""
import csv, glob, json, os, random, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

SCORES = ["structure", "action", "impact", "result", "quantified", "scope", "credibility",
          "readability", "clipping", "tone", "level", "overall"]
CONTENT_IDX = [1, 2, 3, 4, 5, 6]
GATES = ["pass", "not_a_bullet", "incomplete", "nonsense", "banned"]
TYPES = ["bullet", "narrative", "citation", "push", "strat"]
TYPE_OF = {"classic_bullet": 0, "bullet": 0, "performance_statement": 1, "narrative": 1, "citation": 2,
           "push": 3, "stratification": 4, "strat": 4}
# span tags: outer (exclusive) action/impact/result, then scope and numbers, each its own B/I/O layer
OUTER = ["action", "impact", "result"]
SPAN_TAGS = ["O"] + [f"{p}-{f}" for f in OUTER for p in "BI"] + ["O-scope", "B-scope", "I-scope", "O-num", "B-num", "I-num"]

LEAD = re.compile(r"^\s*[-•*–—]+\s*")


def norm(s):
    """Collapse white space and drop a leading dash or bullet mark."""
    return LEAD.sub("", " ".join(str(s).split()))


def _key(rnd):
    raw = json.load(open(os.path.join(ROOT, "panel", rnd, "items.json"), encoding="utf-8"))
    items = {str(x["id"]): x for x in raw}
    out = []
    for r in csv.DictReader(open(os.path.join(ROOT, "panel", rnd, "key.csv"), encoding="utf-8")):
        x = items.get(r["id"])
        if not x:
            continue
        sc = [float(r[k]) if r.get(k, "") not in ("", None) else float("nan") for k in SCORES]
        g = GATES.index(r["gate"]) if r.get("gate") in GATES else -100
        if rnd == "r4":
            d = "".join(c for c in r["id"] if c.isdigit())
            split = "train" if d and int(d[-1]) % 2 == 0 else "r4test"
        else:
            split = x.get("split", "train")
        out.append({"text": norm(x["text"]), "scores": sc, "gate": g, "id": r["id"], "split": split,
                    "src": x.get("src", "")})
    return out


def scored():
    rows = _key("r5") + _key("r4")
    sp = {}
    for r in rows:
        sp.setdefault(r["split"], []).append(r)
    return sp  # train, val, r4test


def bank():
    import pandas as pd
    df = pd.read_parquet(os.path.join(ROOT, "work", "clean.parquet"))
    df = df[df["removed"].fillna("") == ""]
    return df


def typed(df=None):
    df = bank() if df is None else df
    out = {"train": [], "val": [], "test": []}
    for t, s, ty in zip(df.text, df.split, df.type):
        if ty in TYPE_OF:
            k = "train" if s == "train" else ("val" if s == "val" else "test")
            out[k].append((norm(t), TYPE_OF[ty]))
    # Opera's pairs: a legacy bullet and a narrative of the same accomplishment
    pairs = opera_pairs()
    rnd = random.Random(7)
    rnd.shuffle(pairs)
    cut = len(pairs) // 10
    for a, b in pairs[cut:]:
        out["train"].append((b, 1))
    for a, b in pairs[:cut]:
        out["val"].append((b, 1))
    return out


def opera_pairs():
    out = []
    for ln in open(os.path.join(ROOT, "data", "pairs.jsonl"), encoding="utf-8"):
        r = json.loads(ln)
        if r.get("why", "").startswith("Opera training pair"):
            out.append((norm(r["before"]), norm(r["after"])))
    return out


def spans():
    p = os.path.join(ROOT, "panel", "spans", "spans.jsonl")
    out = {"train": [], "val": []}
    if not os.path.exists(p):
        return out
    for ln in open(p, encoding="utf-8"):
        r = json.loads(ln)
        t = r["text"]
        n = norm(t)
        shift = len(t) - len(n)  # norm only strips a prefix from already collapsed text
        sp = {f: [[a - shift, b - shift] for a, b in v if a >= shift] for f, v in r["spans"].items()}
        out["val" if r["split"] == "val" else "train"].append((n, sp))
    return out


def same_pairs():
    """Pairs that say the same thing: Opera's bullet/narrative pairs, and versions in the near-miss
    structure groups (same content, different shape) the arbiter kept."""
    from synth_arb import load
    pairs = [(a, b, "opera") for a, b in opera_pairs()]
    groups, _ = load("nmstruct")
    keep = set(json.load(open(os.path.join(ROOT, "synth", "arb", "nmstruct", "keep.json"))))
    for g in sorted(keep):
        lv = groups.get(g, {})
        if 2 in lv and 3 in lv:
            pairs.append((norm(lv[2]), norm(lv[3]), "nmstruct"))
        if 2 in lv and 1 in lv:
            pairs.append((norm(lv[2]), norm(lv[1]), "nmstruct"))
    rnd = random.Random(11)
    rnd.shuffle(pairs)
    cut = len(pairs) // 10
    return {"train": pairs[cut:], "val": pairs[:cut]}


class Expander:
    """Spells out approved clipped forms (mbr -> member) the way the app does before scoring."""

    def __init__(self):
        import pandas as pd
        terms = json.load(open(os.path.join(ROOT, "data", "approved_terms.json")))["abbreviations"]
        a = pd.read_csv(os.path.join(ROOT, "data", "abbreviations.csv"))
        a = a[~a.expansion.astype(str).str.startswith("(")]
        exp = {}
        for ab, e in zip(a.abbr.astype(str), a.expansion.astype(str)):
            exp.setdefault(ab, e)
            exp.setdefault(ab.lower(), e)
        self.map = {}
        for t in terms:
            e = exp.get(t) or exp.get(t.lower())
            if not e or t.isupper():
                continue
            e = e.strip()
            if t[:1].islower():
                e = e.lower()
            self.map[t] = e
        keys = sorted(self.map, key=len, reverse=True)
        alts = [re.escape(k) + ("" if k.endswith("/") else r"(?![\w'])") for k in keys]
        self.rx = re.compile(r"(?<![\w'/])(?:" + "|".join(alts) + r")")

    def __call__(self, s):
        return self.rx.sub(lambda m: self.map[m.group(0)] + (" " if m.group(0).endswith("/") else ""), s)


def span_tags(tok, text, sp, max_len=96):
    """Token ids and tag ids for the three layers (-100 on special tokens)."""
    e = tok(text, truncation=True, max_length=max_len, return_offsets_mapping=True)
    outer, scope, num = [], [], []
    def layer(field_spans, a, b, started):
        """0 outside, 1 first token of a piece, 2 inside a piece already begun."""
        for (x, y) in field_spans:
            if a < y and x < b:
                if (x, y) in started:
                    return 2
                started.add((x, y))
                return 1
        return 0
    firsts = {f: set() for f in ["action", "impact", "result", "scope", "numbers"]}
    for (a, b) in e["offset_mapping"]:
        if a == b:
            outer.append(-100); scope.append(-100); num.append(-100); continue
        while a < b and text[a] == " ":
            a += 1
        o = 0
        for k, f in enumerate(OUTER):
            v = layer(sp.get(f, []), a, b, firsts[f])
            if v:
                o = 1 + 2 * k + (v - 1)
                break
        outer.append(o)
        s = layer(sp.get("scope", []), a, b, firsts["scope"])
        scope.append(s)
        n = layer(sp.get("numbers", []), a, b, firsts["numbers"])
        num.append(n)
    return e["input_ids"], outer, scope, num, e["offset_mapping"]


def decode_spans(text, offsets, outer, scope, num):
    """Tag ids back to char spans per field."""
    res = {f: [] for f in ["action", "impact", "result", "scope", "numbers"]}
    def run(tags, fields_of):
        cur = None
        for (a, b), t in zip(offsets, tags):
            if a == b:
                continue
            while a < b and text[a] == " ":
                a += 1
            f, bi = fields_of(t)
            if f is None:
                if cur: res[cur[0]].append([cur[1], cur[2]]); cur = None
                continue
            if bi == "B" or cur is None or cur[0] != f:
                if cur: res[cur[0]].append([cur[1], cur[2]])
                cur = [f, a, b]
            else:
                cur[2] = b
        if cur:
            res[cur[0]].append([cur[1], cur[2]])
    def fo(t):
        if t <= 0:
            return None, None
        k = (t - 1) // 2
        return OUTER[k], "BI"[(t - 1) % 2]
    run(outer, fo)
    run(scope, lambda t: ("scope", "BI"[t - 1]) if t > 0 else (None, None))
    run(num, lambda t: ("numbers", "BI"[t - 1]) if t > 0 else (None, None))
    return res

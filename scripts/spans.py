"""Span labels: batches for the markers, then checking and collecting what they return.

  spans.py batches     write panel/spans/b_NNN.txt from round 5 items plus non-bullet train items
  spans.py check       check every returned line against its statement; list batches to redo
  spans.py collect     write panel/spans/spans.jsonl: id, text, char offsets per field

Pieces are found in the text by exact match, first unused occurrence after the previous piece of the
same field; a piece that isn't in the text, or overlaps another field's piece (scope and numbers may
sit inside the others), fails the line.
"""
import glob, json, os, random, sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "panel", "spans")
FIELDS = ["action", "impact", "result", "scope", "numbers"]
OUTER = {"action", "impact", "result"}
PER = 120


def items():
    p = os.path.join(D, "items.json")
    return {str(x["id"]): x for x in json.load(open(p, encoding="utf-8"))}


def batches():
    os.makedirs(os.path.join(D, "out"), exist_ok=True)
    r5 = json.load(open(os.path.join(ROOT, "panel", "r5", "items.json"), encoding="utf-8"))
    out = [{"id": str(x["id"]), "type": "bullet", "text": x["text"], "split": x["split"]} for x in r5]
    seen = {x["id"] for x in out}
    df = pd.read_parquet(os.path.join(ROOT, "work", "clean.parquet"))
    df = df[(df.split == "train") & (df.type != "classic_bullet")]
    rnd = random.Random(5)
    quota = {"citation": 300, "push": 200, "stratification": 150}
    for t, n in quota.items():
        rows = df[df.type == t]
        for _, r in rows.sample(min(n, len(rows)), random_state=5).iterrows():
            if str(r.rid) not in seen:
                out.append({"id": str(r.rid), "type": t, "text": r.text, "split": "train"})
    rnd.shuffle(out)
    json.dump(out, open(os.path.join(D, "items.json"), "w", encoding="utf-8"), ensure_ascii=False)
    for i in range(0, len(out), PER):
        with open(os.path.join(D, f"b_{i // PER + 1:03d}.txt"), "w", encoding="utf-8") as f:
            f.write("id\ttype\ttext\n")
            for x in out[i:i + PER]:
                f.write(f"{x['id']}\t{x['type']}\t{' '.join(x['text'].split())}\n")
    print(len(out), "items in", (len(out) + PER - 1) // PER, "batches")


def locate(text, row):
    """Char offsets per field, or an error string."""
    taken = []  # (a, b, field) for outer fields
    res = {}
    for f in FIELDS:
        cell = (row.get(f) or "").strip()
        res[f] = []
        if not cell:
            continue
        start = 0
        for piece in [p.strip() for p in cell.split(" | ") if p.strip()]:
            a = text.find(piece, start)
            if a < 0:
                a = text.find(piece)
            if a < 0:
                return f"{f} piece not in text: {piece!r}"
            b = a + len(piece)
            if f in OUTER:
                for (x, y, g) in taken:
                    if a < y and x < b:
                        return f"{f} overlaps {g}: {piece!r}"
                taken.append((a, b, f))
            res[f].append([a, b])
            start = b
    return res


def read_out():
    rows = {}
    for p in sorted(glob.glob(os.path.join(D, "out", "b_*.tsv"))):
        b = os.path.basename(p)[:-4]
        lines = open(p, encoding="utf-8").read().splitlines()
        for ln in lines[1:]:
            parts = ln.split("\t")
            if not parts or not parts[0].strip():
                continue
            parts += [""] * (6 - len(parts))
            rows[parts[0].strip()] = (b, dict(zip(FIELDS, parts[1:6])))
    return rows


def check():
    it = items()
    rows = read_out()
    bad, missing = {}, {}
    for i in range(0, len(it), PER):
        pass
    order = json.load(open(os.path.join(D, "items.json"), encoding="utf-8"))
    errs = []
    for k, x in enumerate(order):
        b = f"b_{k // PER + 1:03d}"
        if x["id"] not in rows:
            missing[b] = missing.get(b, 0) + 1
            continue
        text = " ".join(x["text"].split())
        r = locate(text, rows[x["id"]][1])
        if isinstance(r, str):
            bad[b] = bad.get(b, 0) + 1
            errs.append((x["id"], r))
    n = len(order)
    print(f"items {n}, returned {len(rows)}, failed {sum(bad.values())}, missing {sum(missing.values())}")
    for e in errs[:15]:
        print("  ", e)
    print("missing by batch", missing)
    print("failed by batch", dict(sorted(bad.items(), key=lambda kv: -kv[1])[:20]))
    json.dump([e[0] for e in errs], open(os.path.join(D, "failed.json"), "w"))


def collect():
    rows = read_out()
    order = json.load(open(os.path.join(D, "items.json"), encoding="utf-8"))
    n = 0
    with open(os.path.join(D, "spans.jsonl"), "w", encoding="utf-8") as f:
        for x in order:
            if x["id"] not in rows:
                continue
            text = " ".join(x["text"].split())
            r = locate(text, rows[x["id"]][1])
            if isinstance(r, str):
                continue
            f.write(json.dumps({"id": x["id"], "type": x["type"], "split": x["split"], "text": text, "spans": r}, ensure_ascii=False) + "\n")
            n += 1
    print("wrote", n)


if __name__ == "__main__":
    {"batches": batches, "check": check, "collect": collect}[sys.argv[1]]()

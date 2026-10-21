"""Step 3: label statements with a local teacher model through Ollama.

Everything stays on this computer: the requests go to an Ollama server on
127.0.0.1. Results append to work/labels-<model>.jsonl, so a stopped run
picks up where it left off.

  python scripts\\label.py --model gpt-oss:20b --split test
  python scripts\\label.py --model gemma3:27b --split all --workers 8
"""
import argparse, json, re, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DIMS = ["action", "impact", "result", "quantified", "scope", "readability", "guidance"]
SCHEMA = {
    "type": "object",
    "properties": {
        **{d: {"type": "integer", "minimum": 0, "maximum": 5} for d in DIMS},
        "type": {"type": "string", "enum": ["bullet", "narrative", "citation", "push", "strat"]},
        "spans": {"type": "object", "properties": {
            "action": {"type": "string"}, "impact": {"type": "string"}, "result": {"type": "string"},
            "scope": {"type": "string"}, "numbers": {"type": "array", "items": {"type": "string"}}},
            "required": ["action", "impact", "result", "scope", "numbers"]},
        "note": {"type": "string"},
    },
    "required": DIMS + ["type", "spans", "note"],
}
TYPE_NAME = {"classic_bullet": "bullet", "performance_statement": "narrative", "citation": "citation",
             "push": "push", "stratification": "strat"}

# v3: the teacher reports facts (banned content found, clipped words) and code
# turns them into the guidance and readability scores.
BANNED = ["cfc_fundraising", "waps_or_test_score", "pme_attendance_or_completion", "separation_or_retirement",
          "civilian_employment", "decoration_recommendation", "promotion_push", "stratification"]
DIMS5 = ["action", "impact", "result", "quantified", "scope"]
SCHEMA3 = {
    "type": "object",
    "properties": {
        **{d: {"type": "integer", "minimum": 0, "maximum": 5} for d in DIMS5},
        "clipped": {"type": "array", "items": {"type": "string"}},
        "banned": {"type": "array", "items": {"type": "string", "enum": BANNED}},
        "hype": {"type": "boolean"},
        "junk": {"type": "boolean"},
        "type": SCHEMA["properties"]["type"],
        "spans": SCHEMA["properties"]["spans"],
        "note": {"type": "string"},
    },
    "required": DIMS5 + ["clipped", "banned", "hype", "junk", "type", "spans", "note"],
}


TEST_WORDS = re.compile(r"\b(WAPS|tests?|tested|exams?|EOC|scores?|scored|avg|average)\b", re.I)
PME_SCHOOLS = re.compile(r"\b(PME|ALS|NCOA|SNCOA|SOS|ACSC|AWC|IDE|SDE|NCO Academy|Airman Leadership School|"
                         r"Senior NCO Academy|Senior Noncommissioned Officer Academy|Squadron Officer School|"
                         r"Air Command and Staff|Air War College)\b", re.I)
PME_AWARDS = re.compile(r"\b(Levitow|Distinguished Graduate|DG|Academic Achievement|Commandant'?s Award|"
                        r"Leadership Award)\b", re.I)


def derive(lab, row):
    """Readability and guidance from the facts the teacher reported."""
    clipped = sorted({c for c in lab["clipped"] if c and c in row.text})
    lab["clipped"] = clipped
    n = len(clipped)
    lab["readability"] = 5 if n == 0 else 4 if n == 1 else 3 if n <= 3 else 2 if n <= 5 else 1
    banned = set(lab["banned"])
    # Gemma over-reports these two; keep them only when the words are there.
    if not TEST_WORDS.search(row.text):
        banned.discard("waps_or_test_score")
    if not PME_SCHOOLS.search(row.text) or PME_AWARDS.search(row.text):
        banned.discard("pme_attendance_or_completion")
    lab["banned"] = sorted(banned)
    if TYPE_NAME.get(row.type) in ("push", "strat"):
        banned -= {"promotion_push", "stratification"}
    hype = lab["hype"] or "!" in row.text
    lab["guidance"] = 0 if banned else 3 if hype else 5
    return lab


def ask(host, model, system, row, think, schema=SCHEMA):
    user = f"Statement type in the bank: {TYPE_NAME.get(row.type, row.type)}.\nStatement:\n{row.text}"
    body = {"model": model, "stream": False, "format": schema,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": 0, "seed": 7, "num_ctx": 4096}}
    if think:
        body["think"] = think
    req = urllib.request.Request(f"http://{host}/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=600) as r:
        out = json.loads(r.read())
    lab = json.loads(out["message"]["content"])
    for k, v in list(lab["spans"].items()):  # keep only spans copied exactly
        if k == "numbers":
            lab["spans"][k] = [n for n in v if n and n in row.text]
        elif v and v not in row.text:
            lab["spans"][k] = ""
    if schema is SCHEMA3:
        lab = derive(lab, row)
    return {"rid": int(row.rid), "model": model, "secs": round(time.time() - t0, 2),
            "tokens": out.get("eval_count"), **lab}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--split", default="test", help="test, train, val, or all")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--host", default="127.0.0.1:11435")
    ap.add_argument("--think", default="low", help="reasoning effort for gpt-oss; empty for none")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--prompt", default="teacher_prompt.md", help="prompt file in scripts/")
    ap.add_argument("--v3", action="store_true", help="facts schema; code derives readability and guidance")
    ap.add_argument("--tag", default="", help="suffix for the output file")
    ap.add_argument("--half", default="", help="even or odd: only rids of that parity (dev and holdout halves)")
    a = ap.parse_args()
    df = pd.read_parquet(ROOT / "work" / "clean.parquet")
    if a.split != "all":
        df = df[df.split == a.split]
    if a.half:
        df = df[df.rid % 2 == (0 if a.half == "even" else 1)]
    tag = f"-{a.tag}" if a.tag else ""
    out = ROOT / "work" / f"labels-{a.model.replace(':', '_').replace('/', '_')}{tag}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(l)["rid"] for l in out.open(encoding="utf-8") if l.strip()}
    todo = [r for r in df.itertuples() if int(r.rid) not in done]
    if a.limit:
        todo = todo[:a.limit]
    system = (ROOT / "scripts" / a.prompt).read_text(encoding="utf-8")
    schema = SCHEMA3 if a.v3 else SCHEMA
    think = a.think if a.model.startswith("gpt-oss") and a.think else None
    lock, n, t0 = threading.Lock(), [0, 0], time.time()
    print(f"{len(todo)} to label with {a.model} ({len(done)} done before)", flush=True)

    def one(row):
        for attempt in range(3):
            try:
                rec = ask(a.host, a.model, system, row, think, schema)
                break
            except Exception as e:  # malformed output or a dropped request: try again
                rec = {"rid": int(row.rid), "model": a.model, "error": str(e)[:200]}
        with lock:
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            n[0] += 1
            n[1] += "error" in rec
            if n[0] % 50 == 0 or n[0] == len(todo):
                el = time.time() - t0
                print(f"{n[0]}/{len(todo)} done, {n[1]} errors, {n[0] / el:.2f}/s, "
                      f"{(len(todo) - n[0]) / max(n[0] / el, 1e-9) / 3600:.1f} h left", flush=True)

    with ThreadPoolExecutor(a.workers) as ex:
        list(ex.map(one, todo))


if __name__ == "__main__":
    main()

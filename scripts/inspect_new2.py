import json, sqlite3, collections, csv
from pathlib import Path

R = Path(__file__).resolve().parent.parent
N, O = R / "data_new/epr-bank", R / "data"
old = {r[0] for r in sqlite3.connect(next(O.rglob("epr.db"))).execute("select text from examples")}
new = [json.loads(l) for l in open(N / "examples.jsonl", encoding="utf-8")]
nt = {r["text"] for r in new}
print("examples: old", len(old), "new", len(nt), "only new", len(nt - old), "only old", len(old - nt))
print("critique kinds:", collections.Counter((r.get("critique") or "")[:5] for r in new).most_common(6))
hum = [r for r in new if r.get("critique") and not str(r["critique"]).startswith("auto")]
print("non-auto critiques:", len(hum))
for r in hum[:5]:
    print("  ", r["text"][:120], "||", str(r["critique"])[:200])
p = [json.loads(l) for l in open(N / "perspectives.jsonl", encoding="utf-8")]
for k in ["stance", "role", "service", "rank_tier", "topic"]:
    print(k, collections.Counter(r[k] for r in p).most_common(10))
print("hosts", collections.Counter(r["source_url"].split("/")[2] for r in p).most_common(8))
rs = list(csv.DictReader(open(N / "rubric_scores.csv", encoding="utf-8")))
print("rubric_scores rows", len(rs))
print(open(N / "SOURCES.md", encoding="utf-8").read()[:2500])

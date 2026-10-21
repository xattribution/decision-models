"""Summarize what the updated bank zip adds."""
import json, sqlite3, collections
from pathlib import Path

N = Path(__file__).resolve().parent.parent / "data_new/epr-bank"
O = Path(__file__).resolve().parent.parent / "data"
print(open(N / "build_stats.json", encoding="utf-8").read()[:2000])
for name in ["perspectives.jsonl", "examples.jsonl"]:
    rows = [json.loads(l) for l in open(N / name, encoding="utf-8")]
    print(f"\n{name}: {len(rows)} rows; keys {sorted(set(k for r in rows[:200] for k in r))}")
    for r in rows[:2]:
        print("  ", json.dumps(r, ensure_ascii=False)[:700])
    for k in ["kind", "type", "source_type", "label", "rating_kind", "perspective"]:
        c = collections.Counter(str(r.get(k)) for r in rows if k in r)
        if c:
            print(f"  {k}: {c.most_common(12)}")
print("\nrubric_scores.csv:")
print("".join(open(N / "rubric_scores.csv", encoding="utf-8").readlines()[:6]))
for db in [O / "epr.db", N / "epr.db"]:
    con = sqlite3.connect(db)
    tabs = [r[0] for r in con.execute("select name from sqlite_master where type='table'")]
    print(db.parent.name, {t: con.execute(f"select count(*) from [{t}]").fetchone()[0] for t in tabs})
con = sqlite3.connect(N / "epr.db")
for t in [r[0] for r in con.execute("select name from sqlite_master where type='table'")]:
    print(t, [c[1] for c in con.execute(f"pragma table_info([{t}])")])

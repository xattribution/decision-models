"""Write the panel's input files: shuffled batches of the 500 hand-set items
for each scorer, and the 36 Brown Bag bullets for calibration.

  panel_batches.py ROUND SCORERS BATCHES
"""
import csv, json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TYPE = {"classic_bullet": "bullet", "performance_statement": "narrative", "citation": "citation",
        "push": "push", "stratification": "stratification"}


def clean(s):
    return " ".join(str(s).split())


def main():
    rnd, scorers, batches = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    items = json.load(open(ROOT / "scoring/items.json", encoding="utf-8"))
    out = ROOT / f"panel/r{rnd}"
    out.mkdir(parents=True, exist_ok=True)
    for s in range(1, scorers + 1):
        order = items[:]
        random.Random(1000 * rnd + s).shuffle(order)
        size = -(-len(order) // batches)
        for b in range(batches):
            part = order[b * size:(b + 1) * size]
            with open(out / f"s{s}_b{b + 1}.txt", "w", encoding="utf-8", newline="\n") as f:
                f.write("id\tbank type\ttext\n")
                for it in part:
                    f.write(f"{it['id']}\t{TYPE[it['type']]}\t{clean(it['text'])}\n")
    cal = ROOT / "panel/cal"
    cal.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(ROOT / "work/brownbag_scored.csv", encoding="utf-8")))
    with open(cal / "items.txt", "w", encoding="utf-8", newline="\n") as f:
        f.write("id\tbank type\ttext\n")
        for r in rows:
            f.write(f"bb{r['line']}\tbullet\t{clean(r['text'])}\n")
    print(len(items), "items,", scorers, "scorers,", batches, "batches;", len(rows), "calibration bullets")


if __name__ == "__main__":
    main()

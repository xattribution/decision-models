import json, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
df = pd.read_parquet(ROOT / "work" / "clean.parquet").set_index("rid")
f = ROOT / "work" / sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
for line in list(f.open(encoding="utf-8"))[:n]:
    x = json.loads(line)
    if "error" in x:
        continue
    t = df.loc[x["rid"], "text"]
    print(t[:200])
    print("  ", " ".join(f"{k[:4]}={x[k]}" for k in ["action", "impact", "result", "quantified", "scope", "readability", "guidance"]), "|", x["type"], "|", x["note"])
    print("   spans:", {k: v for k, v in x["spans"].items() if v})

"""Compare the USSF member bullets with the legacy bank bullets."""
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_parquet(ROOT / "work" / "clean.parquet")
b = df[df.type == "classic_bullet"].copy()
b["group"] = b.source.map(lambda s: "USSF members" if s == "ussf-bank" else "legacy bank")
clipped = re.compile(r"^(?:[a-z]+'[a-z]+|[a-z]*[bcdfghjklmnpqrstvwxz]{3,}[a-z]*|f|w|ISO|IAW|tng|trng|msn|mbrs?|prsnl|psnl|sq|crs|ops|rqmts?)$", re.I)
b["chars"] = b.text.str.len()
b["slashes"] = b.text.str.count("/")
b["clipped"] = b.text.str.findall(r"[A-Za-z][A-Za-z'&/.-]*").map(lambda ts: sum(bool(clipped.match(t)) for t in ts))
b["has_dashdash"] = b.text.str.contains("--")
b["number"] = b.text.str.contains(r"\d")
b["dollar"] = b.text.str.contains(r"\$")
b["percent"] = b.text.str.contains("%")
b["exclaim"] = b.text.str.contains("!")
g = b.groupby("group").agg(n=("text", "size"), chars=("chars", "mean"), slashes=("slashes", "mean"), clipped=("clipped", "mean"),
                           ar_format=("has_dashdash", "mean"), has_number=("number", "mean"), has_dollar=("dollar", "mean"),
                           has_percent=("percent", "mean"), exclaim=("exclaim", "mean"))
print(g.round(2).T.to_string())

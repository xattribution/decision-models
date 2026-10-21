"""Parse and profile data/space_force_bank.txt (recent USSF bullets).

Writes work/sf_bank.parquet (one row per unique bullet, with the special
spaces used to fit it, its width at 12-point Times New Roman and a few
features) and prints a profile.
"""
import collections, re, unicodedata
from pathlib import Path

import pandas as pd
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
raw = (ROOT / "data" / "space_force_bank.txt").read_bytes()
enc = "utf-8-sig" if raw[:3] == b"\xef\xbb\xbf" else "utf-8"
try:
    text = raw.decode(enc)
except UnicodeDecodeError:
    enc = "cp1252"
    text = raw.decode(enc)
lines = [l.rstrip("\r") for l in text.split("\n") if l.strip()]

# 12-point Times New Roman at 96 dpi, from the font on this computer.
font = TTFont(r"C:\Windows\Fonts\times.ttf")
cmap, hmtx, upem = font.getBestCmap(), font["hmtx"].metrics, font["head"].unitsPerEm
PX = 16.0 / upem  # 12 pt = 16 px at 96 dpi


def px(s):
    w = 0.0
    for ch in s:
        g = cmap.get(ord(ch))
        w += hmtx[g][0] * PX if g else 8.0
    return w


SPECIAL = {c for c in "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u00a0\u200b"}
LINE = 764.0  # DAF 910/911 field width in px, as pdf-bullets and the bank's build.py use

rows = []
for l in lines:
    sp = collections.Counter(ch for ch in l if ch in SPECIAL)
    clean = re.sub(r"[\u2000-\u200b\u202f\u205f\u00a0]", " ", l)
    clean = re.sub(r" {2,}", " ", clean).strip()
    rows.append({"raw": l, "text": clean, "special": dict(sp), "n_special": sum(sp.values()),
                 "px_raw": round(px(l), 1), "px_clean": round(px(clean), 1)})
df = pd.DataFrame(rows)
df["norm"] = df.text.str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
dup = df.duplicated("norm")
u = df[~dup].copy()
u["lines_raw"] = (u.px_raw / LINE).round(2)
u["lines_clean"] = (u.px_clean / LINE).round(2)
u["has_result"] = u.text.str.contains("--")
u["kind"] = u.has_result.map({True: "accomplishment", False: "key duty or other"})
toks = u.text.str.findall(r"[A-Za-z][A-Za-z'&/.-]*")
clipped = re.compile(r"^(?:[a-z]+'[a-z]+|[a-z]*[bcdfghjklmnpqrstvwxz]{3,}[a-z]*|f|w|ISO|IAW|tng|trng|msn|mbrs?|prsnl|psnl|sq|crs|ops|rqmts?)$", re.I)
u["n_slash"] = u.text.str.count("/")
u["clipped"] = toks.map(lambda ts: sum(bool(clipped.match(t)) for t in ts))
u["source"] = "sf_bank"
u.drop(columns=["norm"]).to_parquet(ROOT / "work" / "sf_bank.parquet", index=False)

print(f"encoding {enc}; lines {len(df)}; unique {len(u)}; exact repeats {int(dup.sum())}")
print("bullets using special spaces:", int((u.n_special > 0).sum()))
allsp = collections.Counter()
for d in u.special:
    allsp.update(d)
for ch, n in allsp.most_common():
    print(f"  U+{ord(ch):04X} {unicodedata.name(ch, '?')}: {n} uses, {px(ch):.2f} px")
print("width as written (lines of 764 px):", u.lines_raw.describe().round(2).to_dict())
print("width with normal spaces:", u.lines_clean.describe().round(2).to_dict())
over = u[(u.n_special > 0)]
print("fitted bullets: width with plain spaces minus as written, px:",
      (over.px_clean - over.px_raw).describe().round(1).to_dict())
print("within 1 line as written:", int((u.lines_raw <= 1.0).sum()), "| 1-2 lines:", int(((u.lines_raw > 1) & (u.lines_raw <= 2)).sum()),
      "| over 2:", int((u.lines_raw > 2).sum()))
print(u.kind.value_counts().to_dict())
print("chars per bullet:", u.text.str.len().describe().round(0).to_dict())
print("slashes per bullet:", u.n_slash.mean().round(2), "| clipped words per bullet:", u.clipped.mean().round(2))
verbs = u.text.str.extract(r"^-?\s*([A-Za-z'-]+)")[0].str.lower().value_counts().head(20)
print("lead words:", verbs.to_dict())
terms = collections.Counter(w for t in u.text for w in re.findall(r"\b(?:SPAFORGEN|Delta|DEL|Del|Guardians?|SpOC|STARCOM|SSC|USSPACECOM|NSDC|JTF-SD|SCN|SDA|DCO|OCO|CYS|SOPS|C3|MQT|SFB)\b", t))
print("USSF terms:", dict(terms.most_common(20)))
names = u[u.text.str.contains(r"\b(?:SSgt|TSgt|MSgt|Sgt|Spc[1-4]|Capt|Maj|Lt|Mr|Ms|Dr)\.? [A-Z][a-z]+")]
print("rank + capitalized word (check for names):", len(names))
for t in names.text.head(8):
    print("   ", t[:120])

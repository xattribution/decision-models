"""Step 1: audit the bank, remove personal and private details, collapse
near-duplicates, and split by source.

Reads data/epr.db and writes:
  work/clean.parquet   every kept row, with era, source, cluster and split
  work/removed.csv     every removed row with the reason (for review)
  work/audit.md        the report
Run: .venv\\Scripts\\python.exe scripts\\audit.py
"""
import collections, re, sqlite3, sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
from datasketch import MinHash, MinHashLSH
from faker import Faker

ROOT = Path(__file__).resolve().parent.parent
DATA, WORK = ROOT / "data", ROOT / "work"
WORK.mkdir(exist_ok=True)

df = pd.read_sql("select rowid as rid, * from examples", sqlite3.connect(DATA / "epr.db"))
df["text"] = df["text"].fillna("").str.strip()
# Recent USSF bullets from the maintainer and other Guardians (data/space_force_bank.txt,
# parsed by analyze_sf.py with fitting spaces turned back into plain spaces).
sf = pd.read_parquet(WORK / "sf_bank.parquet")
sf = pd.DataFrame({"rid": range(10_000_000, 10_000_000 + len(sf)), "text": sf.text, "type": "classic_bullet",
                   "form": "USSF 910/911 (current bullet era)", "source_url": "local:space_force_bank.txt",
                   "source_type": "member"})
df = pd.concat([df, sf], ignore_index=True)


def source_of(u):
    p = urlparse(u or "")
    host = (p.netloc or "").removeprefix("www.")
    if u == "local:space_force_bank.txt":
        return "ussf-bank"
    if host == "github.com":
        return "github/" + "/".join(p.path.strip("/").split("/")[:2])
    return host or "unknown"


df["source"] = df["source_url"].map(source_of)
df["era"] = df["form"].map(lambda f: "citation" if "citation" in f else ("narrative" if "narrative" in f or "EPB" in f else "bullet"))

# ---- screens -------------------------------------------------------------
fk = Faker("en_US")
first = {n for n in fk.first_names()} if hasattr(fk, "first_names") else set()
if not first:
    from faker.providers.person.en_US import Provider as P
    first = set(P.first_names)
from faker.providers.person.en_US import Provider as P
first |= set(P.first_names)
last = set(P.last_names)
# Words that are also common names but read as ordinary words in bullets.
common = {"Will", "Grant", "Mark", "Bill", "Chase", "Lead", "Major", "Young", "Long", "Hope", "Faith", "Joy",
          "May", "June", "August", "April", "Rich", "Rose", "Guy", "Jack", "Frank", "Gene", "Dean", "Wing",
          "Base", "Field", "Lane", "Hall", "King", "Price", "Park", "Hunter", "Miles", "Page", "Ray", "Reed",
          "Summer", "Winter", "Sky", "Star", "Golden", "Gray", "Grey", "Black", "White", "Green", "Brown",
          "Bell", "Cash", "Penny", "Sterling", "Max", "Rocky", "Iron", "Steel", "Stone", "Ford", "Lincoln",
          "Washington", "Jefferson", "Jackson", "Madison", "Monroe", "Tyler", "Wayne", "Pierce", "Carter",
          "Dakota", "Nevada", "Georgia", "Virginia", "Carolina", "Florida", "Alaska", "Texas", "Montana",
          "Austin", "Dallas", "Houston", "Denver", "Phoenix", "Eagle", "Hawk", "Falcon", "Patriot",
          "Guard", "Marshal", "Judge", "Bishop", "Chief", "Sergeant", "Airman", "Captain", "General", "Colonel"}
names_first = first - common
names_last = last - common

RANK = r"(?:Amn|A1C|SrA|SSgt|TSgt|MSgt|SMSgt|CMSgt|2d ?Lt|2Lt|1st ?Lt|1Lt|Capt|Maj|Lt ?Col|Col|Brig ?Gen|Maj ?Gen|Lt ?Gen|Gen|Sgt|Spc[1-4]?|Mr|Mrs|Ms|Dr|Airman|Senior Airman|Staff Sergeant|Technical Sergeant|Master Sergeant|Senior Master Sergeant|Chief Master Sergeant|Lieutenant|Captain|Major|Colonel|General|Specialist)"
honor = re.compile(r"\b(?:Award|Trophy|Cup|Memorial|Scholarship|Symposium|Course|Crse|Crs|Awd|Of the Year|Academy|Program|Prgm|Leadership|Hall|Field|AFB|Base|Center|Ctr|Building|Bldg|Bridge|Street|Road|Ave)\b", re.I)
rank_name = re.compile(RANK + r"\.? +([A-Z][a-z]{2,})(?: +[A-Z]\.?)?(?: +([A-Z][a-z]{2,}))?")
screens = {
    "id_number": re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b\d{9,10}\b"),
    "contact": re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}|\b\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b|\bDSN:? ?\d{3}[- ]?\d{4}\b|\b(?:Bldg|Building|Rm|Room) ?#? ?\d{2,}", re.I),
    "name_after_placeholder": re.compile(r"\[NAME\] +(?:[A-Z]\.? +)?(?!United\b|Polish\b)[A-Z][a-z]{2,}(?:-[A-Z][a-z]+)?\b(?! +(?:distinguished|is|was|has|led|served))"),
}


def screen(row):
    t = row.text
    if len(t) < 20:
        return "too_short"
    if row.source_type == "forum" and re.search(r"\b(?:I|I'm|Im|ill|lol|you|your|my)\b", t) and not re.match(r"^[-•]", t):
        return "chat_not_statement"
    for k, p in screens.items():
        if p.search(t):
            return k
    for m in rank_name.finditer(t):
        tail = t[m.end():m.end() + 40]
        words = [w for w in (m.group(1), m.group(2)) if w]
        if honor.search(tail) or honor.search(t[max(0, m.start() - 10):m.start()]):
            continue  # an award, course or place named for someone
        if any(w in names_first or w in names_last for w in words):
            return "personal_name"
    # A first name and a last name side by side, or a first name opening a narrative.
    for m in re.finditer(r"\b([A-Z][a-z]{2,}) +(?:[A-Z]\. +)?([A-Z][a-z]{2,})\b", t):
        a, b = m.group(1), m.group(2)
        if a in names_first and b in names_last and not honor.search(t[m.end():m.end() + 30]):
            return "personal_name"
    if row.era == "narrative":
        m = re.match(r"^(?:[-•] ?)?([A-Z][a-z]{2,})\b", t)
        if m and m.group(1) in names_first:
            return "personal_name"
    return ""


df["removed"] = df.apply(screen, axis=1)
EXCLUDED_SOURCES = {"usebrevet.com": "robots.txt opts out of AI crawlers; vendor examples"}
df.loc[df.source.isin(EXCLUDED_SOURCES) & (df.removed == ""), "removed"] = "excluded_source"

# ---- near-duplicates -----------------------------------------------------
def norm(t):
    t = t.lower()
    t = re.sub(r"\d+(?:[.,]\d+)?", "#", t)
    t = re.sub(r"[^a-z#]+", " ", t)
    return t.split()


keep = df[df.removed == ""].copy()
lsh = MinHashLSH(threshold=0.8, num_perm=64)
mh = {}
for rid, t in zip(keep.rid, keep.text):
    w = norm(t)
    sh = {" ".join(w[i:i + 3]) for i in range(max(1, len(w) - 2))}
    m = MinHash(num_perm=64)
    for s in sh:
        m.update(s.encode())
    mh[rid] = m
    lsh.insert(rid, m)
parent = {}


def find(x):
    while parent.get(x, x) != x:
        x = parent[x]
    return x


for rid, m in mh.items():
    for o in lsh.query(m):
        a, b = find(rid), find(o)
        if a != b:
            parent[max(a, b)] = min(a, b)
keep["cluster"] = keep.rid.map(find)
prio = {"member": 0, "official": 0, "guide": 1, "forum": 2, "bank": 3, "repo": 4}
keep["prio"] = keep.source_type.map(prio).fillna(5)
keep["clen"] = keep.text.str.len()
keep = keep.sort_values(["cluster", "prio", "clen"], ascending=[True, True, False])
csize = keep.groupby("cluster").rid.transform("size")
csources = keep.groupby("cluster").source.transform(lambda s: len(set(s)))
first_in = ~keep.duplicated("cluster")
dups = keep[~first_in].copy()
dups["removed"] = "near_duplicate"
keep = keep[first_in].copy()
keep["cluster_size"] = csize[first_in].values
keep["cluster_sources"] = csources[first_in].values

# ---- split ---------------------------------------------------------------
# Training never sees the hand-scored test items or anything near them
# (clusters are collapsed above, across sites). One whole bank site is held
# out as a validation set, so model choices are checked on a site it never
# trained on. Narrative statements are test and validation only.
VAL_SOURCE = "afbulletsafe.com"
keep["split"] = "train"
keep.loc[keep.source == VAL_SOURCE, "split"] = "val"
keep.loc[keep.era == "narrative", "split"] = "val"

removed = pd.concat([df[df.removed != ""], dups])
removed[["rid", "source", "type", "removed", "text"]].to_csv(WORK / "removed.csv", index=False)
keep.drop(columns=["prio", "clen"]).to_parquet(WORK / "clean.parquet", index=False)

# ---- report --------------------------------------------------------------
def table(s):
    return "\n".join(f"| {k} | {v:,} |" for k, v in s.items())

rep = [f"# Audit of epr.db, {pd.Timestamp.now():%d %b %y %H:%M}", "",
       f"Rows in: {len(df):,}. Kept: {len(keep):,}. Removed: {len(removed):,}.", "",
       "## Removed, by reason", "| Reason | Rows |", "|---|---|", table(removed.removed.value_counts()), "",
       "## Kept, by source and split", "| Source | Train | Val |", "|---|---|---|"]
ct = keep.groupby(["source", "split"]).size().unstack(fill_value=0)
for src, r in ct.sort_values("train", ascending=False).iterrows():
    rep.append(f"| {src} | {r.get('train', 0):,} | {r.get('val', 0):,} |")
rep += ["", "## Kept, by type and era", "| Type | Era | Rows |", "|---|---|---|"]
for (t, e), n in keep.groupby(["type", "era"]).size().sort_values(ascending=False).items():
    rep.append(f"| {t} | {e} | {n:,} |")
rep += ["", f"Near-duplicate clusters spanning more than one site: {(keep.cluster_sources > 1).sum():,}.",
        f"Excluded sources: " + "; ".join(f"{k} ({v})" for k, v in EXCLUDED_SOURCES.items())]
(WORK / "audit.md").write_text("\n".join(rep), encoding="utf-8")
print("\n".join(rep))
sample = removed[removed.removed.isin(["personal_name", "name_after_placeholder", "contact", "id_number"])]
print("\n-- samples of personal-detail removals --")
for r in sample.sample(min(15, len(sample)), random_state=2).itertuples():
    print(r.removed, "|", r.text[:110])

"""Add the rest of Jared's abbreviation list (Rx through yrly) to data/approved_terms.json."""
import json
from pathlib import Path

P = Path(__file__).resolve().parent.parent / "data/approved_terms.json"
NEW = """Appt Rx Rxs sat sched sched'd spc spec spt spt'd sq Sq/CC sr stan/eval std stds Supt svc svs s/w sync sync'd sys
tech tgt tgts thru tm tmwrk trans trn'd trng tng US veh vol vol'd vs w/ w/in w/o wg Wg/CC wk wkly wpn wpns wx xfer xfers
yr yrly""".split()
t = json.loads(P.read_text(encoding="utf-8"))
before = len(t["abbreviations"])
t["abbreviations"] = sorted(set(t["abbreviations"]) | set(NEW))
t["source"] = "Jared's acronym and abbreviation examples list, 21 Oct 26 (full A-Z); a baseline, variants are fine"
P.write_text(json.dumps(t, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(before, "->", len(t["abbreviations"]), "abbreviations;", len(t["acronyms"]), "acronyms")

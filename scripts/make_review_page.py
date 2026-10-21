"""Write scoring/review.html: a spot check of 50 panel decisions. Each card shows
the statement and the panel's scores and reason; Jared gives a thumbs up (the
panel got it right) or down (it didn't). Saves scoring/review.csv.

  make_review_page.py [ROUND, default 1]
"""
import json, random, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 1
P = ROOT / f"panel/r{N}"
DIMS = ["action", "impact", "result", "quantified", "scope", "readability", "guidance"]
LEVEL = ["Fluff", "Membership", "Supervisory", "Management", "Leadership"]

key = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
items = {str(it["id"]): it for it in json.load(open(ROOT / "scoring/items.json", encoding="utf-8"))}


def reasons(pattern):
    out = {}
    for f in sorted(P.glob(pattern)):
        for ln in f.read_text(encoding="utf-8").splitlines()[1:]:
            p = ln.split("\t")
            if len(p) >= 12 and p[0].strip():
                out.setdefault(p[0].strip(), p[11].strip())
    return out


fable, opus = reasons("fable_*.tsv"), reasons("out/s7_*.tsv")
MODE = sys.argv[2] if len(sys.argv) > 2 else "spot50"
rnd = random.Random(50 if MODE == "spot50" else 1000 * N + 15)
ids = list(key.index)
sf = [i for i in ids if items[i]["source"] == "ussf-bank"]
rest = [i for i in ids if items[i]["source"] != "ussf-bank"]
if MODE == "spot50":
    OUTNAME, CSVNAME, STORE = "review.html", "review.csv", "review-v1"
    pick = rnd.sample(sf, 15)
    pick += rnd.sample([i for i in rest if key.loc[i, "source"] == "fable" and key.loc[i, "junk"] == 0], 20)
    pick += rnd.sample([i for i in rest if key.loc[i, "source"] == "median" and key.loc[i, "junk"] == 0], 10)
    pick += rnd.sample([i for i in rest if key.loc[i, "junk"] == 1], 5)
else:  # 15 settled disputes he hasn't seen: 5 Space Force, 10 others
    OUTNAME, CSVNAME, STORE = f"review_r{N}.html", f"review_r{N}.csv", f"review-r{N}"
    seen = set(pd.read_csv(ROOT / "scoring/review.csv", dtype={"id": str}).id)
    ok = [i for i in ids if key.loc[i, "source"] == "fable" and key.loc[i, "junk"] == 0 and i not in seen]
    pick = rnd.sample([i for i in ok if i in sf], 5) + rnd.sample([i for i in ok if i not in sf], 10)
rnd.shuffle(pick)
cards = []
for i in pick:
    k = key.loc[i]
    cards.append({"id": i, "text": " ".join(str(items[i]["text"]).split()), "bank": items[i]["type"].replace("_", " "),
                  "scores": [int(k[d]) for d in DIMS], "level": LEVEL[int(k["level"])], "junk": int(k["junk"]),
                  "reason": fable.get(i) or opus.get(i, ""), "settled": k["source"] == "fable"})

html = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel spot check</title>
<style>
:root{--bg:#f6f6f4;--fg:#1d1d1b;--muted:#6b6b66;--line:#d8d8d2;--card:#fff;--accent:#1f5fbf;--accent-fg:#fff;--up:#1f7a3d;--down:#b3261e;--bar:#1f5fbf;--track:#e4e4de}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#ecece8;--muted:#9a9a94;--line:#3a3a36;--card:#1d1d1b;--accent:#5b8ff0;--accent-fg:#0b0b0b;--up:#5cc27f;--down:#ff8a80;--bar:#5b8ff0;--track:#2c2c29}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:860px;margin:0 auto;padding:16px}
header{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.count{font-weight:600}.meta{color:var(--muted)}.sp{flex:1}
#text{background:var(--card);border:1px solid var(--line);padding:18px;font-size:19px;min-height:90px;white-space:pre-wrap;margin-bottom:14px}
.verdict{display:flex;gap:16px;flex-wrap:wrap;align-items:baseline;margin-bottom:10px}
.verdict b{font-size:18px}.verdict .junk{color:var(--down);font-weight:600}
.row{display:grid;grid-template-columns:110px 1fr 24px;gap:10px;align-items:center;padding:3px 0}
.track{height:10px;background:var(--track)}.fill{height:10px;background:var(--bar)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.reason{margin:12px 0 4px;color:var(--fg)}.reason span{color:var(--muted)}
.vote{display:flex;gap:10px;margin-top:14px;align-items:center;flex-wrap:wrap}
.vote button{width:84px;height:52px;border:1px solid var(--line);background:var(--card);color:var(--fg);font-size:24px;cursor:pointer}
.vote button.up.on{background:var(--up);border-color:var(--up)}.vote button.down.on{background:var(--down);border-color:var(--down)}
#note{flex:1;min-width:200px;height:44px;border:1px solid var(--line);background:var(--card);color:var(--fg);padding:0 10px;font-size:15px}
footer{display:flex;gap:8px;margin-top:16px;align-items:center;flex-wrap:wrap}
footer button,#folder{height:44px;padding:0 16px;border:1px solid var(--line);background:var(--card);color:var(--fg);font-size:15px;cursor:pointer}
#save{color:var(--muted)}
.tip{position:relative;width:24px;height:24px;border:1px solid var(--line);border-radius:50%;text-align:center;font-size:13px;line-height:22px;color:var(--muted);cursor:help}
.tip span{display:none;position:absolute;right:30px;bottom:-6px;width:min(380px,70vw);background:var(--card);border:1px solid var(--line);padding:8px 10px;color:var(--fg);z-index:2;text-align:left;line-height:1.4}
.tip:hover span{display:block}
@media (max-width:600px){.row{grid-template-columns:96px 1fr 20px}}
</style></head><body><main>
<header><span class="count" id="count"></span><span class="meta" id="meta"></span><span class="sp"></span><button id="folder">Choose the scoring folder</button></header>
<div id="text"></div>
<div class="verdict"><b id="level"></b><span id="junk" class="junk"></span></div>
<div id="bars"></div>
<div class="reason" id="reason"></div>
<div class="vote"><button class="down" id="down" aria-label="Panel got it wrong">&#128078;</button><button class="up" id="up" aria-label="Panel got it right">&#128077;</button>
<input id="note" placeholder="What's off (optional)" aria-label="Note"></div>
<footer><button id="prev">Back</button><button id="next">Next</button><span class="sp"></span><span id="save"></span>
<span class="tip">i<span>Thumbs up if the panel's scores and level look right for this statement, thumbs down if not. A vote moves to the next card. The note is optional.</span></span></footer>
</main>
<script>
const CARDS = __CARDS__;
const NAMES = ["Action","Impact","Result","Numbers","Scope","Readability","Guidance"];
const KEY = "review-v1";
let votes = {}, pos = 0, dir = null;
try { votes = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const $ = id => document.getElementById(id);
function draw() {
  const c = CARDS[pos], v = votes[c.id] || {};
  $("count").textContent = `${pos + 1} / ${CARDS.length}`;
  $("meta").textContent = `${c.bank} | ${Object.values(votes).filter(x => x.vote !== undefined).length} reviewed`;
  $("text").textContent = c.text;
  $("level").textContent = c.level;
  $("junk").textContent = c.junk ? "Not a real statement" : "";
  $("bars").innerHTML = c.scores.map((s, i) => `<div class="row"><span>${NAMES[i]}</span><div class="track"><div class="fill" style="width:${s * 20}%"></div></div><span class="num">${s}</span></div>`).join("");
  $("reason").innerHTML = c.reason ? `<span>Panel: </span>${c.reason.replace(/</g, "&lt;")}` : "";
  $("up").classList.toggle("on", v.vote === 1); $("down").classList.toggle("on", v.vote === 0);
  $("note").value = v.note || "";
}
function go(p) { pos = Math.max(0, Math.min(CARDS.length - 1, p)); window.scrollTo(0, 0); draw(); }
function vote(x) { const c = CARDS[pos]; votes[c.id] = Object.assign(votes[c.id] || {}, {vote: x}); persist(); draw(); setTimeout(() => go(pos + 1), 250); }
function csv() {
  const q = s => /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  return ["id,vote,note", ...CARDS.filter(c => votes[c.id]).map(c => [c.id, votes[c.id].vote ?? "", q(votes[c.id].note || "")].join(","))].join("\n") + "\n";
}
let pending = null;
function persist() { try { localStorage.setItem(KEY, JSON.stringify(votes)); } catch (e) {} clearTimeout(pending); pending = setTimeout(writeFile, 300); }
async function writeFile() {
  if (!dir) { $("save").textContent = "Not saved to a file yet"; return; }
  try { const f = await dir.getFileHandle("review.csv", {create: true}); const w = await f.createWritable();
    await w.write(csv()); await w.close(); $("save").textContent = "Saved " + new Date().toTimeString().slice(0, 5);
  } catch (e) { $("save").textContent = "Couldn't save: " + e.message; }
}
async function readFile() {
  try { const t = await (await (await dir.getFileHandle("review.csv")).getFile()).text();
    for (const l of t.trim().split(/\r?\n/).slice(1)) { const [id, v, ...n] = l.split(","); votes[id] = {vote: v === "" ? undefined : +v, note: n.join(",").replace(/^"|"$/g, "").replace(/""/g, '"')}; }
  } catch (e) {}
}
$("folder").onclick = async () => {
  if (!window.showDirectoryPicker) { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv()], {type: "text/csv"})); a.download = "review.csv"; a.click(); return; }
  dir = await showDirectoryPicker({id: "handscore", mode: "readwrite"}); await readFile(); $("folder").textContent = dir.name;
  persist(); const i = CARDS.findIndex(c => !votes[c.id] || votes[c.id].vote === undefined); go(i < 0 ? 0 : i);
};
$("up").onclick = () => vote(1); $("down").onclick = () => vote(0);
$("note").oninput = () => { const c = CARDS[pos]; votes[c.id] = Object.assign(votes[c.id] || {}, {note: $("note").value}); persist(); };
$("prev").onclick = () => go(pos - 1); $("next").onclick = () => go(pos + 1);
draw();
</script></body></html>
"""
html = html.replace("__CARDS__", json.dumps(cards, ensure_ascii=False).replace("</", "<\\/"))
html = html.replace('"review.csv"', f'"{CSVNAME}"').replace('"review-v1"', f'"{STORE}"')
(ROOT / "scoring" / OUTNAME).write_text(html, encoding="utf-8")
print("wrote", ROOT / "scoring" / OUTNAME, len(cards), "cards")

"""Write scoring/pairs.html: 100 pairs of passing bullets; Jared clicks the one a
board would rate higher (or "about the same"). Grades are hidden so they can't
sway the pick. Saves scoring/pairs.csv.

  make_pairs_page.py ROUND
"""
import json, random, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
N = int(sys.argv[1])
P = ROOT / f"panel/r{N}"
k = pd.read_csv(P / "key.csv", dtype={"id": str}).set_index("id")
items = {o["id"]: o for o in json.load(open(P / "items.json", encoding="utf-8"))}
k["src"] = [items[i]["src"] for i in k.index]
k["len"] = [len(items[i]["text"]) for i in k.index]
p = k[(k.gate == "pass") & (k.src != "afbulletsafe-rated")]
rnd = random.Random(7)
ids = list(p.index)
usf = [i for i in ids if p.loc[i, "src"] == "ussf-bank"]
oth = [i for i in ids if p.loc[i, "src"] != "ussf-bank"]
pairs, used = [], set()


def add(a, b, kind):
    key = tuple(sorted((a, b)))
    if a != b and key not in used:
        used.add(key)
        pairs.append((a, b, kind) if rnd.random() < 0.5 else (b, a, kind))
        return True
    return False


while sum(1 for x in pairs if x[2] == "close") < 30:
    a, b = rnd.sample(ids, 2)
    if abs(p.loc[a, "overall"] - p.loc[b, "overall"]) <= 0.5:
        add(a, b, "close")
while sum(1 for x in pairs if x[2] == "ussf_vs_other") < 25:
    a, b = rnd.choice(usf), rnd.choice(oth)
    if abs(p.loc[a, "overall"] - p.loc[b, "overall"]) <= 1.0:
        add(a, b, "ussf_vs_other")
longs = [i for i in ids if p.loc[i, "len"] > 150]
shorts = [i for i in ids if p.loc[i, "len"] <= 120]
while sum(1 for x in pairs if x[2] == "long_vs_short") < 20:
    add(rnd.choice(longs), rnd.choice(shorts), "long_vs_short")
while sum(1 for x in pairs if x[2] == "clear") < 25:
    a, b = rnd.sample(ids, 2)
    if abs(p.loc[a, "overall"] - p.loc[b, "overall"]) >= 1.0:
        add(a, b, "clear")
rnd.shuffle(pairs)
cards = [{"a": a, "b": b, "kind": kind, "ta": items[a]["text"], "tb": items[b]["text"]} for a, b, kind in pairs]

html = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Which bullet is stronger</title>
<style>
:root{--bg:#f6f6f4;--fg:#1d1d1b;--muted:#6b6b66;--line:#d8d8d2;--card:#fff;--accent:#1f5fbf;--accent-fg:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#ecece8;--muted:#9a9a94;--line:#3a3a36;--card:#1d1d1b;--accent:#5b8ff0;--accent-fg:#0b0b0b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}
header{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.count{font-weight:600}.meta{color:var(--muted)}.sp{flex:1}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.pick{background:var(--card);border:1px solid var(--line);padding:18px;font-size:18px;text-align:left;color:var(--fg);cursor:pointer;min-height:140px;font-family:inherit}
.pick.on{background:var(--accent);color:var(--accent-fg);border-color:var(--accent)}
.row{display:flex;gap:8px;margin-top:12px;align-items:center;flex-wrap:wrap}
.row button,#folder{height:44px;padding:0 16px;border:1px solid var(--line);background:var(--card);color:var(--fg);font-size:15px;cursor:pointer}
.row button.on{background:var(--accent);color:var(--accent-fg);border-color:var(--accent)}
#save{color:var(--muted)}
.tip{position:relative;width:24px;height:24px;border:1px solid var(--line);border-radius:50%;text-align:center;font-size:13px;line-height:22px;color:var(--muted);cursor:help}
.tip span{display:none;position:absolute;right:30px;bottom:-6px;width:min(380px,70vw);background:var(--card);border:1px solid var(--line);padding:8px 10px;color:var(--fg);z-index:2;text-align:left;line-height:1.4}
.tip:hover span{display:block}
@media (max-width:640px){.pair{grid-template-columns:1fr}}
</style></head><body><main>
<header><span class="count" id="count"></span><span class="meta" id="meta"></span><span class="sp"></span><button id="folder">Choose the scoring folder</button></header>
<div class="pair"><button class="pick" id="pa"></button><button class="pick" id="pb"></button></div>
<div class="row"><button id="same">About the same</button><span class="sp"></span><button id="prev">Back</button><button id="next">Next</button><span id="save"></span>
<span class="tip">i<span>Click the bullet a promotion board would rate higher. Use About the same when you can't separate them. A pick moves to the next pair. Keys: Left or 1 for the left bullet, Right or 2 for the right, 0 for about the same.</span></span></div>
</main>
<script>
const PAIRS = __PAIRS__;
const KEY = "pairs-r__R__";
let picks = {}, pos = 0, dir = null;
try { picks = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const $ = id => document.getElementById(id);
const pid = p => p.a + "|" + p.b;
function draw() {
  const p = PAIRS[pos], v = picks[pid(p)];
  $("count").textContent = `${pos + 1} / ${PAIRS.length}`;
  $("meta").textContent = `${Object.keys(picks).length} picked`;
  $("pa").textContent = p.ta; $("pb").textContent = p.tb;
  $("pa").classList.toggle("on", v === "a"); $("pb").classList.toggle("on", v === "b"); $("same").classList.toggle("on", v === "same");
}
function go(i) { pos = Math.max(0, Math.min(PAIRS.length - 1, i)); window.scrollTo(0, 0); draw(); }
function pick(v) { picks[pid(PAIRS[pos])] = v; persist(); draw(); setTimeout(() => go(pos + 1), 200); }
function csv() { return ["left,right,kind,pick", ...PAIRS.filter(p => picks[pid(p)]).map(p => [p.a, p.b, p.kind, picks[pid(p)]].join(","))].join("\n") + "\n"; }
let pending = null;
function persist() { try { localStorage.setItem(KEY, JSON.stringify(picks)); } catch (e) {} clearTimeout(pending); pending = setTimeout(writeFile, 300); }
async function writeFile() {
  if (!dir) { $("save").textContent = "Not saved to a file yet"; return; }
  try { const f = await dir.getFileHandle("pairs.csv", {create: true}); const w = await f.createWritable(); await w.write(csv()); await w.close();
    $("save").textContent = "Saved " + new Date().toTimeString().slice(0, 5); } catch (e) { $("save").textContent = "Couldn't save: " + e.message; }
}
async function readFile() {
  try { const t = await (await (await dir.getFileHandle("pairs.csv")).getFile()).text();
    for (const l of t.trim().split(/\r?\n/).slice(1)) { const [a, b, , v] = l.split(","); if (v) picks[a + "|" + b] = v; } } catch (e) {}
}
$("folder").onclick = async () => {
  if (!window.showDirectoryPicker) { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv()], {type: "text/csv"})); a.download = "pairs.csv"; a.click(); return; }
  dir = await showDirectoryPicker({id: "handscore", mode: "readwrite"}); await readFile(); $("folder").textContent = dir.name;
  persist(); const i = PAIRS.findIndex(p => !picks[pid(p)]); go(i < 0 ? 0 : i);
};
$("pa").onclick = () => pick("a"); $("pb").onclick = () => pick("b"); $("same").onclick = () => pick("same");
$("prev").onclick = () => go(pos - 1); $("next").onclick = () => go(pos + 1);
document.addEventListener("keydown", e => {
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === "ArrowLeft" || e.key === "1") pick("a"); else if (e.key === "ArrowRight" || e.key === "2") pick("b");
  else if (e.key === "0") pick("same"); else return; e.preventDefault();
});
draw();
</script></body></html>
"""
html = html.replace("__PAIRS__", json.dumps(cards, ensure_ascii=False).replace("</", "<\\/")).replace("__R__", str(N))
(ROOT / "scoring/pairs.html").write_text(html, encoding="utf-8")
print("wrote", ROOT / "scoring/pairs.html", len(cards), "pairs:", pd.Series([c["kind"] for c in cards]).value_counts().to_dict())

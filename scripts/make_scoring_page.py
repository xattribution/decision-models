"""Step 2b: write scoring/score.html, one self-contained page that shows the
hand set one statement at a time and saves scores to scoring/scores.csv.
Each dimension is a slider from weak to strong; the csv keeps the slider
position (0.0 to 5.0) and analysis rounds it to the nearest whole score.

  make_scoring_page.py [ITEM FILE in scoring/, default items.json]
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "scoring"
items = json.loads((OUT / (sys.argv[1] if len(sys.argv) > 1 else "items.json")).read_text(encoding="utf-8"))

# One tip per dimension, from rubric.md (5 / 3 / 0-1) and rules.md.
DIMS = [
    ("action", "Action", "Strong: a strong past-tense verb, the member's own action. Middle: a generic verb (managed, performed). Weak: passive, participated or assisted, or a task description."),
    ("impact", "Impact", "Strong: an explicit effect on the mission or people. Middle: implied. Weak: none."),
    ("result", "Result", "Strong: a measurable outcome. Middle: a vague outcome. Weak: none."),
    ("quantified", "Numbers", "Strong: real, checkable numbers. Middle: numbers present but round or filler (100%). Weak: none, or placeholders (x, ###)."),
    ("scope", "Scope", "Strong: the level is stated and fits (unit, wing, MAJCOM or FLDCOM, DAF, DoD or joint). Middle: implied. Weak: unclear, or a claim far above what the action could reach."),
    ("readability", "Readability", "Strong: plain language, only approved acronyms. Middle: some abbreviations. Weak: acronym soup or clipped words. Score the text as written."),
    ("guidance", "Guidance", "Strong: no banned content. Middle: a minor issue (hype, !). Weak: banned content: CFC, WAPS, PME, separation, a decoration recommendation, a push or strat outside a push or strat line, a veiled strat."),
]

html = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hand scoring</title>
<style>
:root{--bg:#f6f6f4;--fg:#1d1d1b;--muted:#6b6b66;--line:#d8d8d2;--card:#fff;--accent:#1f5fbf;--accent-fg:#fff;--flag:#b3261e;--up:#1f7a3d;--down:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--fg:#ecece8;--muted:#9a9a94;--line:#3a3a36;--card:#1d1d1b;--accent:#5b8ff0;--accent-fg:#0b0b0b;--flag:#ff8a80;--up:#5cc27f;--down:#ff8a80}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:860px;margin:0 auto;padding:16px}
header{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.count{font-weight:600}.meta{color:var(--muted)}.sp{flex:1}
.flagon{color:var(--flag);font-weight:600}
#text{background:var(--card);border:1px solid var(--line);padding:18px;font-size:19px;min-height:110px;white-space:pre-wrap;margin-bottom:14px}
.dim{display:grid;grid-template-columns:120px 28px 1fr;align-items:center;gap:10px;padding:6px 0}
.name{font-weight:600}
.tip{position:relative;width:24px;height:24px;border:1px solid var(--line);border-radius:50%;text-align:center;font-size:13px;line-height:22px;color:var(--muted);cursor:help}
.tip span{display:none;position:absolute;left:30px;top:-6px;width:min(420px,70vw);background:var(--card);border:1px solid var(--line);padding:8px 10px;color:var(--fg);z-index:2;text-align:left;line-height:1.4;font-weight:400}
.tip:hover span{display:block}
footer .tip span{left:auto;right:30px}
.sl{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;color:var(--muted);font-size:14px}
input[type=range]{width:100%;height:44px;margin:0;accent-color:var(--accent);cursor:pointer}
.unset input[type=range]{accent-color:var(--line);opacity:.55}
.thumbs{display:grid;grid-template-columns:120px 28px auto;gap:10px;align-items:center;margin-top:10px}
.thumbs div{display:flex;gap:8px}
.thumbs button{width:64px;height:44px;border:1px solid var(--line);background:var(--card);color:var(--fg);font-size:20px;cursor:pointer}
.thumbs button.up.on{background:var(--up);border-color:var(--up)}
.thumbs button.down.on{background:var(--down);border-color:var(--down)}
footer{display:flex;gap:8px;margin-top:16px;align-items:center;flex-wrap:wrap}
footer button,#folder{height:44px;padding:0 16px;border:1px solid var(--line);background:var(--card);color:var(--fg);font-size:15px;cursor:pointer}
footer .primary{background:var(--accent);color:var(--accent-fg);border-color:var(--accent);font-weight:600}
footer .primary:disabled{opacity:.45;cursor:default}
#save{color:var(--muted)}
@media (max-width:600px){.dim{grid-template-columns:1fr 28px}.sl{grid-column:1/-1}.thumbs{grid-template-columns:1fr 28px}.thumbs div{grid-column:1/-1}}
</style></head><body><main>
<header><span class="count" id="count"></span><span class="meta" id="meta"></span><span class="sp"></span>
<span id="flagged"></span><button id="folder">Choose the scoring folder</button></header>
<div id="text"></div>
<div id="dims"></div>
<div class="thumbs"><span class="name">Overall</span><span></span>
<div><button class="down" id="down" aria-label="Weak overall">&#128078;</button><button class="up" id="up" aria-label="Good overall">&#128077;</button></div></div>
<footer><button class="primary" id="next">Save and next</button><button id="skip">Skip</button><button id="flag">Flag</button>
<button id="prev">Back</button><span class="sp"></span><span id="save"></span>
<span class="tip">i<span>Drag or click each slider: left is weak, right is strong. Thumbs up or down is your overall call and is optional. Save and next unlocks once every slider is set. Flag marks an item to discuss; Skip leaves it unscored.</span></span></footer>
</main>
<script>
const ITEMS = __ITEMS__;
const DIMS = __DIMS__;
const KEY = "handscore-v2";
let scores = {};
let pos = 0, started = Date.now(), dir = null;
try { scores = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) {}
const $ = id => document.getElementById(id);

function build() {
  $("dims").innerHTML = DIMS.map(d => `<div class="dim" data-d="${d[0]}"><span class="name">${d[1]}</span>
    <span class="tip">i<span>${d[2]}</span></span><span class="sl"><span>Weak</span>
    <input type="range" min="0" max="5" step="0.1" value="2.5" data-d="${d[0]}" aria-label="${d[1]}"><span>Strong</span></span></div>`).join("");
  document.querySelectorAll("#dims input").forEach(el => {
    const setIt = () => { set(el.dataset.d, Math.round(+el.value * 10) / 10); draw(); };
    el.addEventListener("input", setIt); el.addEventListener("change", setIt); el.addEventListener("pointerup", setIt);
  });
}
function rec() { const it = ITEMS[pos]; return scores[it.id] || (scores[it.id] = {}); }
function set(d, v) { rec()[d] = v; persist(); }
function done(r) { return !!r.skip || DIMS.every(d => r[d[0]] !== undefined); }
function first() { const i = ITEMS.findIndex(it => !scores[it.id] || !done(scores[it.id])); return i < 0 ? 0 : i; }

function draw() {
  const it = ITEMS[pos], r = rec();
  $("text").textContent = it.text;
  $("count").textContent = `${pos + 1} / ${ITEMS.length}`;
  const n = ITEMS.filter(x => scores[x.id] && done(scores[x.id])).length;
  $("meta").textContent = `${it.type.replace("_", " ")} | ${n} scored`;
  $("flagged").textContent = r.flag ? "Flagged" : ""; $("flagged").className = r.flag ? "flagon" : "";
  document.querySelectorAll(".dim").forEach(el => {
    const v = r[el.dataset.d], inp = el.querySelector("input");
    el.classList.toggle("unset", v === undefined);
    if (document.activeElement !== inp) inp.value = v === undefined ? 2.5 : v;
  });
  $("up").classList.toggle("on", r.overall === 1); $("down").classList.toggle("on", r.overall === 0);
  $("next").disabled = !DIMS.every(d => r[d[0]] !== undefined);
}
function go(p) { if (document.activeElement) document.activeElement.blur(); pos = Math.max(0, Math.min(ITEMS.length - 1, p));
  started = Date.now(); window.scrollTo(0, 0); draw(); }
function next() {
  const r = rec();
  if (!done(r)) return;
  if (r.secs === undefined) r.secs = Math.round((Date.now() - started) / 100) / 10;
  persist(); go(pos + 1);
}
function csv() {
  const cols = ["id", "type", "source", "era", ...DIMS.map(d => d[0]), "overall", "skip", "flag", "secs"];
  const q = v => v === undefined || v === null ? "" : /[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : v;
  return [cols.join(","), ...ITEMS.filter(it => scores[it.id] && (done(scores[it.id]) || scores[it.id].flag)).map(it => {
    const r = scores[it.id];
    return [it.id, it.type, it.source, it.era, ...DIMS.map(d => r[d[0]]), r.overall, r.skip ? 1 : "", r.flag ? 1 : "", r.secs].map(q).join(",");
  })].join("\n") + "\n";
}
let pending = null;
function persist() {
  try { localStorage.setItem(KEY, JSON.stringify(scores)); } catch (e) {}
  clearTimeout(pending); pending = setTimeout(writeFile, 300);
}
async function writeFile() {
  if (!dir) { $("save").textContent = "Not saved to a file yet"; return; }
  try { const f = await dir.getFileHandle("scores.csv", {create: true}); const w = await f.createWritable();
    await w.write(csv()); await w.close(); $("save").textContent = "Saved " + new Date().toTimeString().slice(0, 5);
  } catch (e) { $("save").textContent = "Couldn't save: " + e.message; }
}
async function readFile() {
  try {
    const f = await (await dir.getFileHandle("scores.csv")).getFile();
    const lines = (await f.text()).trim().split(/\r?\n/); const cols = lines.shift().split(",");
    for (const l of lines) {
      const v = l.split(","), r = {};
      cols.forEach((c, i) => { if (v[i] === undefined || v[i] === "" || ["id", "type", "source", "era"].includes(c)) return;
        r[c] = (c === "skip" || c === "flag") ? true : +v[i]; });
      scores[v[0]] = Object.assign(scores[v[0]] || {}, r);
    }
  } catch (e) {}
}
$("folder").onclick = async () => {
  if (!window.showDirectoryPicker) { const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([csv()], {type: "text/csv"}));
    a.download = "scores.csv"; a.click(); return; }
  dir = await showDirectoryPicker({id: "handscore", mode: "readwrite"}); await readFile(); $("folder").textContent = dir.name;
  persist(); go(first());
};
$("up").onclick = () => { const r = rec(); r.overall = r.overall === 1 ? undefined : 1; persist(); draw(); };
$("down").onclick = () => { const r = rec(); r.overall = r.overall === 0 ? undefined : 0; persist(); draw(); };
$("next").onclick = next;
$("skip").onclick = () => { rec().skip = true; persist(); go(pos + 1); };
$("flag").onclick = () => { const r = rec(); r.flag = !r.flag; persist(); draw(); };
$("prev").onclick = () => go(pos - 1);
document.addEventListener("keydown", e => {
  if (e.ctrlKey || e.metaKey || e.altKey || e.target.type === "range") return;
  if (e.key === "Enter") next(); else if (e.key === "ArrowLeft") go(pos - 1); else if (e.key === "ArrowRight") go(pos + 1); else return;
  e.preventDefault();
});
build(); go(first());
</script></body></html>
"""
html = html.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("</", "<\\/")).replace("__DIMS__", json.dumps(DIMS))
(OUT / "score.html").write_text(html, encoding="utf-8")
print("wrote", OUT / "score.html", len(items), "items")

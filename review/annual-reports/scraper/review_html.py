"""Standalone HTML reviewer for scraped dairy annual report rows."""

TEMPLATE = r"""<!DOCTYPE html>
<meta charset="utf-8">
<title>Dairy Report Scrape Review</title>
<style>
 :root{--bg:#12141a;--fg:#e8e8ea;--dim:#9aa0aa;--line:#2a2e38;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--acc:#58a6ff;--panel:#171a21}
 *{box-sizing:border-box} body{margin:0;font:13px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
 header{display:flex;gap:10px;align-items:center;padding:7px 12px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--bg);z-index:5;flex-wrap:wrap}
 header h1{font-size:14px;margin:0;font-weight:600;white-space:nowrap}
 .pill{padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;white-space:nowrap}
 .PASS{background:#1b3a24;color:var(--ok)} .WARN{background:#3a2f14;color:var(--warn)} .FAIL{background:#3d1a1a;color:var(--bad)}
 .CROP{background:#1b2430;color:var(--acc)}
 .fld input[readonly]{color:var(--dim);border-style:dashed}
 .v-accepted{background:#1b3a24;color:var(--ok)} .v-flagged{background:#3a2f14;color:var(--warn)}
 .v-unusable{background:#3d1a1a;color:var(--bad)} .v-none{background:#20242e;color:var(--dim)}
 button{background:#20242e;color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:4px 9px;cursor:pointer;font-size:12px}
 button:hover{border-color:var(--acc)} button.on{border-color:var(--acc);color:var(--acc);background:#1b2430}
 .seg{display:flex;gap:0} .seg button{border-radius:0;margin-left:-1px} .seg button:first-child{border-radius:6px 0 0 6px} .seg button:last-child{border-radius:0 6px 6px 0}
 input[type=search]{background:#191d26;border:1px solid var(--line);color:var(--fg);border-radius:6px;padding:4px 8px;font-size:12px;width:190px}
 input[type=search]:focus{outline:none;border-color:var(--acc)}
 #wrap{display:grid;grid-template-columns:288px 1fr 462px;height:calc(100vh - 46px)}
 #wrap.noidx{grid-template-columns:0 1fr 462px}
 #idx{overflow-y:auto;background:var(--panel);border-right:1px solid var(--line)}
 #wrap.noidx #idx{display:none}
 .ir{display:grid;grid-template-columns:34px 1fr;gap:6px;align-items:center;padding:5px 8px;border-bottom:1px solid #1f232b;cursor:pointer}
 .ir:hover{background:#1d2129} .ir.cur{background:#22303f;box-shadow:inset 2px 0 0 var(--acc)}
 .ir .g{font-size:9.5px;font-weight:700;text-align:center;border-radius:3px;padding:2px 0}
 .ir .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}
 .ir .sub{color:var(--dim);font-size:10.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
 .ir .done{color:var(--ok)} .ir .flag{color:var(--warn)} .ir .unus{color:var(--bad)} .ir .edit{color:var(--acc)}
 #eviz{overflow:auto;padding:12px;background:#0b0d11}
 #eviz img{width:100%;border:1px solid var(--line);border-radius:5px;margin-bottom:10px;background:#fff;cursor:zoom-in}
 #eviz img.zoom{position:fixed;inset:2vh 2vw;width:96vw;height:96vh;object-fit:contain;z-index:50;cursor:zoom-out;background:#fff}
 #side{overflow:auto;padding:12px;border-left:1px solid var(--line)}
 .fld{display:grid;grid-template-columns:1fr 148px;gap:6px;align-items:center;padding:3px 0}
 .fld label{color:var(--dim);font-size:11.5px}
 .hint{font-size:10.5px;color:var(--acc)} .hint.bad{color:var(--bad)}
 .fld input{background:#191d26;border:1px solid var(--line);color:var(--fg);border-radius:4px;padding:4px 6px;font:12px ui-monospace,Menlo,monospace;text-align:right;width:100%}
 .fld input:focus{outline:none;border-color:var(--acc)} .fld input.edited{border-color:var(--warn);color:var(--warn)}
 .fld input.txt{text-align:left}
.fld select{background:#191d26;border:1px solid var(--line);color:var(--fg);border-radius:4px;padding:4px 6px;font:12px ui-monospace,Menlo,monospace;width:100%}
.fld select:focus{outline:none;border-color:var(--acc)}
.fld.wide{grid-template-columns:1fr 215px}
 h3{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);margin:14px 0 4px;border-bottom:1px solid var(--line);padding-bottom:3px}
 .chk{display:flex;justify-content:space-between;gap:8px;padding:3px 6px;border-radius:4px;margin:2px 0;font-size:11.5px;background:#191d26}
 .chk.good{color:var(--ok)} .chk.bad{color:var(--bad)} .chk.warn{color:var(--warn)}
 .note{color:var(--dim);font-size:11px;padding:2px 0 2px 8px;border-left:2px solid var(--line);margin:3px 0}
 .meta{color:var(--dim);font-size:11.5px;margin-bottom:6px} .meta b{color:var(--fg);font-weight:600}
 #bar{height:3px;background:var(--line)} #bar div{height:100%;background:var(--acc);width:0}
 kbd{background:#20242e;border:1px solid var(--line);border-radius:3px;padding:0 4px;font-size:10.5px}
 .srcbar{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--line)}
 .srcbar a{color:var(--acc);text-decoration:none;font-size:12px;white-space:nowrap}
 .srcbar a:hover{text-decoration:underline}
 .srcbar code{color:var(--dim);font-size:10.5px;user-select:all;word-break:break-all}
 #toast{position:fixed;bottom:12px;left:50%;transform:translateX(-50%);background:#20242e;border:1px solid var(--line);padding:6px 12px;border-radius:6px;opacity:0;transition:.2s;z-index:60;pointer-events:none}
 #toast.show{opacity:1}
 .rev{padding:6px 8px;border-radius:5px;background:#191d26;margin-bottom:8px;display:flex;gap:6px;align-items:center;flex-wrap:wrap}
</style>
<header>
  <h1>Dairy Report Scrape Review</h1>
  <button id="togidx" class="on" title="Show or hide the list">&#9776;</button>
  <div class="seg">
    <button id="f-all">All</button>
    <button id="f-todo" class="on">To do</button>
    <button id="f-done">Reviewed</button>
    <button id="f-ratio" title="Reports whose applied-to-removed ratio has not been looked at">Ratio</button>
    <button id="f-crop" title="Facility-wide crop N removal values not yet examined, problems first">Crop N</button>
  </div>
  <input type="search" id="q" placeholder="Search dairy or PDF…" autocomplete="off">
  <span id="pos" class="meta" style="margin:0"></span>
  <span id="grade" class="pill"></span>
  <span id="vpill" class="pill"></span>
  <button id="link">Link CSV</button>
  <button id="export">Export decisions</button>
  <button id="import">Import decisions</button>
  <input type="file" id="file" accept=".csv" style="display:none">
  <span class="meta" style="margin-left:auto;margin-bottom:0">
    <kbd>1</kbd> accept <kbd>2</kbd> flag <kbd>3</kbd> unusable <kbd>0</kbd> clear
    <kbd>u</kbd> reopen last <kbd>r</kbd> ratio ok <kbd>c</kbd> crop N ok <kbd>e</kbd> edit <kbd>/</kbd> search
    <kbd>&larr;</kbd><kbd>&rarr;</kbd> move
  </span>
</header>
<div id="bar"><div></div></div>
<div id="wrap"><div id="idx"></div><div id="eviz"></div><div id="side"></div></div>
<div id="toast"></div>
<script>
const ROWS = __ROWS__;
const FIELDS = __FIELDS__;
const NUMFIELDS = FIELDS.filter(f => f.num).map(f => f.k);
const HERD = __HERD__;
const AMMONIA = 0.70;
const LS = "dairyScrapeReview.v1";
const LS_UI = "dairyScrapeReview.ui.v1";
const LS_RATIO = "dairyScrapeReview.ratio.v1";
const LS_FORM = "dairyScrapeReview.form.v1";
const LS_CROP = "dairyScrapeReview.crop.v1";
const SEED = __SEED__;
const RATIO_KEY = __RATIO_KEY__;
const RATIO_FORMS = __RATIO_FORMS__;
const FORM_TYPES = __FORM_TYPES__;
const CROP_KEY = __CROP_KEY__;
/* Reports parsed before this study carry only the crop removal value. They are
   reviewed under the Crop N filter alone and take no verdict, so every count
   and filter for the main review runs over MAIN. */
const MAIN = ROWS.filter(r => !r.cropOnly);
const CROP_TOL = 0.01;

let verdicts = {};        // pdf -> {verdict, fields:{k:v}, ts, note}
let ratioOK = {};         // pdf -> true once the ratio has been looked at
let formType = {};        // pdf -> the report form the reviewer confirmed
let cropOK = {};          // pdf -> true once the crop N removal has been looked at
let filter = "todo";      // all | todo | done | ratio | crop
let query = "";
let showIdx = true;
let curPdf = null;        // the row on screen, tracked by PDF name not position
let lastMarked = null;    // the row most recently given a verdict, for undo
let handle = null;

try { verdicts = JSON.parse(localStorage.getItem(LS) || "{}"); } catch (e) { verdicts = {}; }
try { ratioOK = JSON.parse(localStorage.getItem(LS_RATIO) || "{}"); } catch (e) { ratioOK = {}; }
try { formType = JSON.parse(localStorage.getItem(LS_FORM) || "{}"); } catch (e) { formType = {}; }
try { cropOK = JSON.parse(localStorage.getItem(LS_CROP) || "{}"); } catch (e) { cropOK = {}; }
/* Decisions exported on an earlier pass, written into the page at build time.
   Merged field by field rather than whole entries: a correction or note added
   to the CSV outside the browser is absent from localStorage, and replacing
   the file wholesale on the next export would drop it. Anything localStorage
   already holds wins, so work done here is never overwritten by the seed. */
for (const pdf in SEED.verdicts) {
  const s = SEED.verdicts[pdf];
  const e = verdicts[pdf] || (verdicts[pdf] = {verdict: "", fields: {}});
  if (!e.verdict && s.verdict) e.verdict = s.verdict;
  if (!e.note && s.note) e.note = s.note;
  e.fields = e.fields || {};
  for (const k in s.fields) if (!(k in e.fields)) e.fields[k] = s.fields[k];
}
for (const pdf in SEED.ratioOK) if (!(pdf in ratioOK)) ratioOK[pdf] = true;
for (const pdf in SEED.formType || {}) if (!(pdf in formType)) formType[pdf] = SEED.formType[pdf];
for (const pdf in SEED.cropOK || {}) if (!(pdf in cropOK)) cropOK[pdf] = true;
try {
  const ui = JSON.parse(localStorage.getItem(LS_UI) || "{}");
  if (ui.filter) filter = ui.filter;
  if (typeof ui.showIdx === "boolean") showIdx = ui.showIdx;
  if (ui.curPdf) curPdf = ui.curPdf;
} catch (e) {}

const num = v => {
  if (v === null || v === undefined || v === "") return null;
  const n = parseFloat(String(v).replace(/,/g, ""));
  return isNaN(n) ? null : n;
};
const fmt = v => (v === null || v === undefined || v === "") ? ""
  : (typeof v === "number" ? v.toLocaleString("en-US", {maximumFractionDigits: 2}) : String(v));
const entry = pdf => verdicts[pdf] || null;
const verdictOf = pdf => (entry(pdf) && entry(pdf).verdict) || "";
const editCount = pdf => Object.keys((entry(pdf) || {}).fields || {}).length;
const isDone = pdf => !!verdictOf(pdf);
/* The ratio was added after the first review pass, so a report can carry a
   verdict and still have an unexamined ratio. Only the forms that print one
   are ever asked for. */
const hasRatio = r => !r.cropOnly && RATIO_FORMS.indexOf(r.form) >= 0;
const needsRatio = r => hasRatio(r) && !ratioOK[r.pdf];
function ackRatio(pdf) {
  ratioOK[pdf] = true;
  localStorage.setItem(LS_RATIO, JSON.stringify(ratioOK));
  localStorage.setItem(LS_FORM, JSON.stringify(formType));
}
/* Crop N removal is asked for wherever it was extracted for a summary report. */
const hasCrop = r => !!r.crop;
const needsCrop = r => hasCrop(r) && !cropOK[r.pdf];
function ackCrop(pdf) {
  cropOK[pdf] = true;
  localStorage.setItem(LS_CROP, JSON.stringify(cropOK));
}
/* The detector reads the form from the cover pages and is wrong on scanned
   packets and on consultant forms that reprint the official tables, so the
   reviewer can overrule it. An empty choice means it has not been judged and
   the detector's reading stands. */
const formOf = r => formType[r.pdf] || "";
function setFormType(pdf, v) {
  if (v) formType[pdf] = v; else delete formType[pdf];
  localStorage.setItem(LS_FORM, JSON.stringify(formType));
}
function value(r, k) {
  const e = entry(r.pdf) && entry(r.pdf).fields;
  return (e && k in e) ? e[k] : r.f[k];
}
function saveUI() {
  localStorage.setItem(LS_UI, JSON.stringify({filter, showIdx, curPdf}));
}

const TOTAL_KEY = "Total Herd Size";

function sameAsScraped(parsed, orig) {
  const blank = v => v === null || v === undefined || v === "";
  if (blank(parsed) && blank(orig)) return true;
  if (blank(parsed) || blank(orig)) return false;
  if (typeof parsed === "number" && isFinite(Number(orig)))
    return Number(orig) === parsed;
  return String(parsed) === String(orig);
}

function herdSum(r) {
  /* Blank categories count as zero, because a form that omits a category means
     the dairy keeps none of that animal. All six blank means there is nothing
     to sum, and the total is left alone. */
  const vals = HERD.map(c => num(value(r, c)));
  if (vals.every(v => v === null)) return null;
  return vals.reduce((a, b) => a + (b || 0), 0);
}

function setField(r, k, parsed) {
  verdicts[r.pdf] = verdicts[r.pdf] || {verdict: "", fields: {}};
  verdicts[r.pdf].fields = verdicts[r.pdf].fields || {};
  if (sameAsScraped(parsed, r.f[k])) delete verdicts[r.pdf].fields[k];
  else verdicts[r.pdf].fields[k] = parsed;
}

function recomputeTotal(r) {
  /* The total is derived from the six categories, so clearing all of them
     clears the total rather than leaving a stale partial sum behind. */
  const s = herdSum(r);
  setField(r, TOTAL_KEY, s);
  return s;
}

function applyEdit(r, k, raw) {
  /* Returns the recomputed herd total when this edit changed one of the six
     categories, so the caller can refresh that input. */
  const parsed = NUMFIELDS.includes(k) ? num(String(raw).trim()) : String(raw).trim();
  setField(r, k, parsed);
  if (k === RATIO_KEY) ackRatio(r.pdf);
  if (k === CROP_KEY) ackCrop(r.pdf);
  const isHerd = HERD.indexOf(k) >= 0;
  const total = isHerd ? recomputeTotal(r) : null;
  cleanup(r.pdf);
  return {parsed, total, isHerd};
}

/* ---- the visible list: filter, then free-text search -------------------- */
function visible() {
  const q = query.trim().toLowerCase();
  const out = ROWS.filter(r => {
    if (r.cropOnly && filter !== "crop") return false;
    if (filter === "todo" && isDone(r.pdf)) return false;
    if (filter === "done" && !isDone(r.pdf)) return false;
    if (filter === "ratio" && !needsRatio(r)) return false;
    if (filter === "crop" && !needsCrop(r)) return false;
    if (!q) return true;
    return (String(r.f["Dairy Name"] || "") + " " + r.pdf + " " + r.form)
      .toLowerCase().includes(q);
  });
  // Problem values first; the sort is stable, so build order holds within a status.
  if (filter === "crop") out.sort((a, b) => a.crop.rank - b.crop.rank);
  return out;
}
function curRow() {
  const vis = visible();
  if (!vis.length) return null;
  let r = vis.find(x => x.pdf === curPdf);
  if (!r) { r = vis[0]; curPdf = r.pdf; }
  return r;
}
function step(delta) {
  const vis = visible();
  if (!vis.length) return;
  let i = vis.findIndex(x => x.pdf === curPdf);
  if (i < 0) i = 0;
  i = Math.min(vis.length - 1, Math.max(0, i + delta));
  curPdf = vis[i].pdf;
  saveUI(); render();
}

function checks(r) {
  const out = [];
  const hv = HERD.map(k => num(value(r, k))).filter(v => v !== null);
  const tot = num(value(r, "Total Herd Size"));
  if (hv.length && tot !== null) {
    const s = hv.reduce((a, b) => a + b, 0);
    out.push({ok: Math.abs(s - tot) <= 0.5, hard: true,
              t: `herd total ${fmt(tot)} vs sum ${fmt(s)}`});
  }
  const g = num(value(r, "Total Dry Manure Generated N (lbs)"));
  const a = num(value(r, "Total Dry Manure Generated N After Ammonia Losses (lbs)"));
  if (g !== null && a !== null)
    out.push({ok: Math.abs(a - g * AMMONIA) <= Math.max(1, 0.001 * g), hard: true,
              t: `after-ammonia ${fmt(a)} vs 0.70x${fmt(g)} = ${fmt(+(g*AMMONIA).toFixed(2))}`});
  const mt = num(value(r, "Total Manure Excreted (tons)"));
  if (mt !== null && tot) out.push({ok: mt/tot >= 9.33 && mt/tot <= 25.10, hard: false,
              t: `tons per head ${(mt/tot).toFixed(2)} (expect 9.33-25.10)`});
  if (g !== null && mt) out.push({ok: g/mt >= 10 && g/mt <= 14, hard: false,
              t: `lb N per ton ${(g/mt).toFixed(2)} (expect 10.0-14.0)`});
  return out.concat(cropChecks(r));
}

/* The printed ratio is total N applied from every source over crop removal, so
   a correctly read removal reproduces it. Recomputed from the value on screen,
   so a correction is checked as it is typed. */
function cropChecks(r) {
  const c = r.crop;
  if (!c) return [];
  const R = num(value(r, CROP_KEY));
  const out = [];
  if (c.T !== null && c.Q !== null && R)
    out.push({ok: Math.abs(c.T / R - c.Q) <= CROP_TOL, hard: true,
              t: `crop N: applied ${fmt(c.T)} ÷ removal ${fmt(R)} = ${(c.T / R).toFixed(2)}`
                 + ` vs printed ratio ${c.Q.toFixed(2)}`});
  else
    out.push({ok: false, hard: false,
              t: `crop N: no check possible (${R === 0 ? "removal is 0" : c.status})`});
  if (c.Q !== null && c.S !== null)
    out.push({ok: Math.abs(c.Q - c.S) <= CROP_TOL, hard: false,
              t: `printed ratio ${c.Q.toFixed(2)} vs summary file ${c.S.toFixed(2)}`});
  return out;
}

/* ---- the list panel ----------------------------------------------------- */
function renderIndex(vis, cur) {
  const mark = r => {
    if (filter === "crop" && r.crop)
      return `crop N: ${r.crop.status}` + (r.crop.method === "ocr" ? " · OCR" : "");
    const v = verdictOf(r.pdf), n = editCount(r.pdf);
    const bits = [];
    if (v === "accepted") bits.push('<span class="done">&#10003; accepted</span>');
    else if (v === "flagged") bits.push('<span class="flag">&#9873; flagged</span>');
    else if (v === "unusable") bits.push('<span class="unus">&#10007; unusable</span>');
    if (n) bits.push(`<span class="edit">${n} edit${n > 1 ? "s" : ""}</span>`);
    if (!bits.length) bits.push("not reviewed");
    return bits.join(" · ");
  };
  document.getElementById("idx").innerHTML = vis.map(r => `
    <div class="ir ${r.pdf === cur.pdf ? "cur" : ""}" data-pdf="${encodeURIComponent(r.pdf)}">
      <div class="g ${r.grade}">${r.grade}</div>
      <div><div class="nm">${(r.f["Dairy Name"] || "(no name)")
        .replace(/</g, "&lt;")}</div><div class="sub">${mark(r)}</div></div>
    </div>`).join("") || '<div class="meta" style="padding:10px">Nothing matches.</div>';
  document.querySelectorAll("#idx .ir").forEach(el => el.onclick = () => {
    curPdf = decodeURIComponent(el.dataset.pdf); saveUI(); render();
  });
  const c = document.querySelector("#idx .ir.cur");
  if (c) c.scrollIntoView({block: "nearest"});
}

function render() {
  document.getElementById("wrap").classList.toggle("noidx", !showIdx);
  document.getElementById("togidx").classList.toggle("on", showIdx);
  for (const [id, val] of [["f-all","all"],["f-todo","todo"],["f-done","done"],
                           ["f-ratio","ratio"],["f-crop","crop"]])
    document.getElementById(id).classList.toggle("on", filter === val);
  const done = MAIN.filter(r => isDone(r.pdf)).length;
  const ratioLeft = ROWS.filter(needsRatio).length;
  const cropLeft = ROWS.filter(needsCrop).length;
  document.getElementById("f-all").textContent = `All ${MAIN.length}`;
  document.getElementById("f-todo").textContent = `To do ${MAIN.length - done}`;
  document.getElementById("f-done").textContent = `Reviewed ${done}`;
  document.getElementById("f-ratio").textContent = `Ratio ${ratioLeft}`;
  document.getElementById("f-crop").textContent = `Crop N ${cropLeft}`;
  document.querySelector("#bar div").style.width = (100 * done / MAIN.length) + "%";

  const vis = visible();
  const r = curRow();
  if (!r) {
    document.getElementById("idx").innerHTML =
      '<div class="meta" style="padding:10px">Nothing matches.</div>';
    document.getElementById("eviz").innerHTML =
      "<p style='color:#9aa0aa'>Nothing to show. Switch to <b>All</b> or clear the search.</p>";
    document.getElementById("side").innerHTML = "";
    document.getElementById("pos").textContent = `0 of 0 · ${done}/${MAIN.length} reviewed`;
    document.getElementById("grade").textContent = "";
    document.getElementById("grade").className = "pill";
    document.getElementById("vpill").textContent = "";
    document.getElementById("vpill").className = "pill";
    return;
  }
  renderIndex(vis, r);

  const i = vis.findIndex(x => x.pdf === r.pdf);
  document.getElementById("pos").textContent =
    `${i + 1} of ${vis.length} shown · ${done}/${MAIN.length} reviewed · ${r.pdf}`;
  const gr = document.getElementById("grade");
  gr.textContent = r.grade; gr.className = "pill " + r.grade;
  const v = verdictOf(r.pdf);
  const vp = document.getElementById("vpill");
  vp.textContent = r.cropOnly ? (cropOK[r.pdf] ? "crop N examined" : "crop N not examined")
                             : (v ? v : "not reviewed");
  vp.className = "pill " + (r.cropOnly ? (cropOK[r.pdf] ? "v-accepted" : "v-none")
                                       : (v ? "v-" + v : "v-none"));

  const shown = r.crops.slice();
  if (filter === "crop" && r.crop && r.crop.page)
    shown.sort((a, b) => (b[1] === r.crop.page) - (a[1] === r.crop.page));
  document.getElementById("eviz").innerHTML = srcLink(r) + (shown.length
    ? shown.map(c => `<div><div class="meta">${c[0]} — page ${c[1]}</div>
        <img src="crops/${c[2]}" loading="lazy"></div>`).join("")
    : "<p style='color:#9aa0aa'>No evidence crop was produced for this report. "
      + "Open the source report above to read the page.</p>");

  const ck = checks(r);
  const nEdit = editCount(r.pdf);
  /* A crop-only row shows identity and the ratio as read-only context, and the
     crop removal as its one editable value. */
  const CROP_ONLY_FIELDS = ["Dairy Name", "Dairy Address", RATIO_KEY, CROP_KEY];
  const shownFields = r.cropOnly
    ? FIELDS.filter(f => CROP_ONLY_FIELDS.indexOf(f.k) >= 0) : FIELDS;
  const ro = k => r.cropOnly && k !== CROP_KEY;
  document.getElementById("side").innerHTML = (r.cropOnly ? `
    <div class="rev"><button data-cropok="1" class="${cropOK[r.pdf] ? "on" : ""}">c crop N ok</button>
      ${nEdit ? `<button data-revert="1">revert edit</button>` : ""}</div>` : `
    <div class="rev">
      <button data-set="accepted" class="${v==="accepted"?"on":""}">1 accept</button>
      <button data-set="flagged" class="${v==="flagged"?"on":""}">2 flag</button>
      <button data-set="unusable" class="${v==="unusable"?"on":""}">3 unusable</button>
      <button data-set="">0 clear</button>
      <button data-reopen="1">u reopen last</button>
      ${nEdit ? `<button data-revert="1">revert ${nEdit} edit${nEdit>1?"s":""}</button>` : ""}
      ${hasCrop(r) ? `<button data-cropok="1" class="${cropOK[r.pdf] ? "on" : ""}">c crop N ok</button>` : ""}
    </div>`) + `
    <div class="meta"><b>${(r.f["Dairy Name"] || "(no name)")}</b><br>
      form <b>${r.form}</b> · read by <b>${r.method}</b> · ${r.npages} pages
      ${r.crop ? `<br>crop N removal: <b>${r.crop.status}</b>${r.crop.page
        ? " on page " + r.crop.page : ""}${r.crop.method === "ocr" ? " (read by OCR)" : ""}` : ""}
      ${r.cropOnly ? "" : `<div class="fld wide" style="margin-top:6px">
        <label>Report type${formOf(r) && formOf(r) !== r.form
          ? ' <span class="hint">overrides ' + r.form + '</span>' : ""}</label>
        <select id="formsel">${FORM_TYPES.map(t =>
          `<option value="${t}"${t === formOf(r) ? " selected" : ""}>${
            t || "— detector: " + r.form + " —"}</option>`).join("")}</select>
      </div>`}
      ${r.dup ? '<br><span style="color:#f85149">possible duplicate: ' + r.dup + '</span>' : ""}</div>
    <h3>Automated checks</h3>
    ${ck.length ? ck.map(c => `<div class="chk ${c.ok ? "good" : (c.hard ? "bad" : "warn")}">
        <span>${c.ok ? "✓" : "✗"} ${c.t}</span></div>`).join("")
      : '<div class="chk">no checks possible</div>'}
    <h3>Fields</h3>
    ${shownFields.map(f => `<div class="fld"><label>${f.k}${
        f.k === TOTAL_KEY ? ' <span id="sumhint" class="hint"></span>' : ""}</label>
      <input data-k="${f.k}" class="${f.num ? "" : "txt"}"${ro(f.k) ? " readonly" : ""} value="${
        String(value(r, f.k) ?? "").replace(/"/g, "&quot;")}"></div>`).join("")}
    <h3>Extraction notes</h3>
    ${(r.notes.length ? r.notes : ["(none)"]).map(n => `<div class="note">${n}</div>`).join("")}`;

  const fsel = document.getElementById("formsel");
  if (fsel) fsel.onchange = () => {
    setFormType(r.pdf, fsel.value);
    persist(); render();
    toast(fsel.value ? "report type: " + fsel.value : "report type cleared");
  };
  document.querySelectorAll("#side [data-set]").forEach(btn =>
    btn.onclick = () => mark(btn.dataset.set));
  const cbtn = document.querySelector("#side [data-cropok]");
  if (cbtn) cbtn.onclick = () => ackCropAndStep();
  const rop = document.querySelector("#side [data-reopen]");
  if (rop) rop.onclick = () => reopenLast();
  const rev = document.querySelector("#side [data-revert]");
  if (rev) rev.onclick = () => {
    if (verdicts[r.pdf]) verdicts[r.pdf].fields = {};
    cleanup(r.pdf); persist(); render(); toast("edits reverted");
  };
  document.querySelectorAll("#side input:not([readonly])").forEach(inp => {
    const k = inp.dataset.k;
    if (entry(r.pdf) && entry(r.pdf).fields && k in entry(r.pdf).fields)
      inp.classList.add("edited");
    inp.addEventListener("input", () => {
      const res = applyEdit(r, k, inp.value);
      const f = (entry(r.pdf) || {}).fields || {};
      inp.classList.toggle("edited", k in f);
      if (res.isHerd) {
        // The six categories drive the total, so reflect the new sum at once.
        const ti = document.querySelector('#side input[data-k="' + TOTAL_KEY + '"]');
        if (ti) {
          ti.value = res.total === null ? "" : res.total;
          ti.classList.toggle("edited", TOTAL_KEY in f);
        }
      }
      updateSumHint(r); refreshChecks(r); persist();
    });
  });
  updateSumHint(r);
  document.querySelectorAll("#eviz img").forEach(im =>
    im.onclick = () => im.classList.toggle("zoom"));
}

function updateSumHint(r) {
  const el = document.getElementById("sumhint");
  if (!el) return;
  const s = herdSum(r), t = num(value(r, TOTAL_KEY));
  if (s === null) { el.textContent = ""; el.className = "hint"; return; }
  const agrees = t !== null && Math.abs(t - s) <= 0.5;
  el.textContent = agrees ? `= sum of the six (${fmt(s)})`
                          : `six sum to ${fmt(s)}`;
  el.className = "hint" + (agrees ? "" : " bad");
}
function refreshChecks(r) {
  const ck = checks(r), host = document.querySelectorAll("#side .chk");
  ck.forEach((c, i) => { if (host[i]) {
    host[i].className = "chk " + (c.ok ? "good" : (c.hard ? "bad" : "warn"));
    host[i].firstElementChild.textContent = (c.ok ? "✓ " : "✗ ") + c.t; } });
}
function cleanup(pdf) {
  const e = verdicts[pdf];
  if (e && !e.verdict && !Object.keys(e.fields || {}).length && !e.note) delete verdicts[pdf];
}

/* ---- decisions ---------------------------------------------------------- */
function csv() {
  const cols = ["Source PDF", "verdict", "field", "scraped_value", "corrected_value",
                "reviewed_utc", "note", "ratio_ok", "form_type", "crop_ok"];
  const esc = s => { s = String(s ?? ""); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const lines = [cols.join(",")];
  /* A ratio acknowledgement is a decision in its own right, so a report that
     carries nothing else still earns a row. */
  const pdfs = new Set(Object.keys(verdicts).concat(Object.keys(ratioOK),
                                                   Object.keys(formType),
                                                   Object.keys(cropOK)));
  for (const pdf of pdfs) {
    const v = verdicts[pdf] || {verdict: "", fields: {}};
    const f = v.fields || {};
    const ok = ratioOK[pdf] ? "1" : "";
    const ft = formType[pdf] || "";
    const ck = cropOK[pdf] ? "1" : "";
    if (!v.verdict && !Object.keys(f).length && !v.note && !ok && !ft && !ck) continue;
    const row = ROWS.find(r => r.pdf === pdf);
    const ts = v.ts || new Date().toISOString();
    const nt = v.note || "";
    if (!Object.keys(f).length) lines.push([pdf, v.verdict, "", "", "", ts, nt, ok, ft, ck].map(esc).join(","));
    else for (const k in f)
      lines.push([pdf, v.verdict, k, row ? row.f[k] : "", f[k], ts, nt, ok, ft, ck].map(esc).join(","));
  }
  return lines.join("\n") + "\n";
}
async function persist() {
  localStorage.setItem(LS, JSON.stringify(verdicts));
  saveUI();
  if (handle) { try {
    const w = await handle.createWritable(); await w.write(csv()); await w.close();
  } catch (e) { toast("could not write the linked CSV: " + e.message); } }
}
function parseCsv(text) {
  /* Small RFC4180 reader: fields may be quoted and contain commas or newlines. */
  const rows = [];
  let row = [], cell = "", q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (c === '"') q = false;
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === ",") { row.push(cell); cell = ""; }
    else if (c === "\n") { row.push(cell); cell = ""; rows.push(row); row = []; }
    else if (c !== "\r") cell += c;
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.some(x => x !== ""));
}

function importCsv(text) {
  const rows = parseCsv(text);
  if (!rows.length) { toast("that file has no rows"); return; }
  const head = rows[0].map(h => h.trim());
  const ix = n => head.indexOf(n);
  const iPdf = ix("Source PDF"), iV = ix("verdict"), iF = ix("field"),
        iC = ix("corrected_value"), iT = ix("reviewed_utc"), iN = ix("note"),
        iR = ix("ratio_ok"), iFT = ix("form_type"), iCK = ix("crop_ok");
  if (iPdf < 0) { toast("no 'Source PDF' column in that file"); return; }
  const known = new Set(ROWS.map(r => r.pdf));
  let touched = 0, unknown = 0;
  for (const r of rows.slice(1)) {
    const pdf = (r[iPdf] || "").trim();
    if (!pdf) continue;
    if (!known.has(pdf)) { unknown++; continue; }
    const e = verdicts[pdf] || (verdicts[pdf] = {verdict: "", fields: {}});
    if (iV >= 0 && r[iV]) e.verdict = r[iV].trim();
    if (iT >= 0 && r[iT]) e.ts = r[iT].trim();
    if (iN >= 0 && r[iN] && r[iN].trim()) e.note = r[iN].trim();
    if (iR >= 0 && r[iR] && r[iR].trim()) ratioOK[pdf] = true;
    if (iFT >= 0 && r[iFT] && r[iFT].trim()) formType[pdf] = r[iFT].trim();
    if (iCK >= 0 && r[iCK] && r[iCK].trim()) cropOK[pdf] = true;
    const k = iF >= 0 ? (r[iF] || "").trim() : "";
    if (k) {
      const raw = iC >= 0 ? (r[iC] || "").trim() : "";
      e.fields[k] = NUMFIELDS.includes(k) ? num(raw) : raw;
    }
    touched++;
  }
  for (const pdf in verdicts) cleanup(pdf);
  localStorage.setItem(LS_RATIO, JSON.stringify(ratioOK));
  localStorage.setItem(LS_FORM, JSON.stringify(formType));
  localStorage.setItem(LS_CROP, JSON.stringify(cropOK));
  persist(); render();
  toast(`loaded ${touched} decision row${touched === 1 ? "" : "s"}`
        + (unknown ? `; ${unknown} referred to reports not in this page` : ""));
}

function toast(m) {
  const t = document.getElementById("toast"); t.textContent = m; t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1700);
}
function reopenLast() {
  // Jump back to the row just marked. Marking under the "To do" filter moves on
  // to the next report, so this is how you return to correct what you just did.
  if (!lastMarked) { toast("nothing marked yet in this session"); return; }
  if (filter === "todo" && isDone(lastMarked)) filter = "all";
  query = "";
  const q = document.getElementById("q"); if (q) q.value = "";
  curPdf = lastMarked; saveUI(); render();
  toast("reopened " + (ROWS.find(r => r.pdf === lastMarked).f["Dairy Name"] || lastMarked));
}

function srcLink(r) {
  /* A link to the report itself, relative to this page and anchored to the
     nutrient-application page when one was located. The path is also shown as
     copyable text, for browsers that will not open the link. */
  const anchor = r.ratiopage ? "#page=" + r.ratiopage : "";
  const at = r.ratiopage ? ` at page ${r.ratiopage}` : "";
  return `<div class="srcbar">
    <a href="${r.url}${anchor}" target="_blank" rel="noopener">&#128196; open source report${at}</a>
    <code title="click to select">${decodeURIComponent(r.url).replace("file://", "")}</code></div>`;
}

function ackRatioAndStep() {
  /* Records that the ratio on screen was read and left as it stands. Editing
     the ratio input records the same thing, so this is the "it is correct"
     half of the pass. The report's verdict is untouched. */
  const r = curRow(); if (!r) return;
  if (!hasRatio(r)) { toast("this form prints no applied-to-removed ratio"); return; }
  ackRatio(r.pdf);
  if (filter === "ratio") {
    const vis = visible();
    if (vis.length) {
      const after = vis.find(x => ROWS.indexOf(x) > ROWS.findIndex(y => y.pdf === r.pdf));
      curPdf = (after || vis[vis.length - 1]).pdf;
    }
    saveUI();
  }
  render();
  toast("ratio confirmed");
}

function ackCropAndStep() {
  /* Records that the crop removal on screen was read and is right as it stands.
     Under the Crop N filter the next report takes its place in the list. */
  const r = curRow(); if (!r) return;
  if (!hasCrop(r)) { toast("no facility-wide crop N removal for this report"); return; }
  const at = visible().findIndex(x => x.pdf === r.pdf);
  ackCrop(r.pdf);
  if (filter === "crop") {
    const vis = visible();
    if (vis.length) curPdf = vis[Math.min(Math.max(at, 0), vis.length - 1)].pdf;
    saveUI();
  }
  persist(); render();
  toast("crop N removal confirmed");
}

function mark(verdict) {
  const r = curRow(); if (!r) return;
  if (r.cropOnly) { toast("this report is reviewed for crop N removal only: press c"); return; }
  if (!verdict) {
    if (verdicts[r.pdf]) verdicts[r.pdf].verdict = "";
    cleanup(r.pdf); persist();
    render(); toast("verdict cleared"); return;
  }
  verdicts[r.pdf] = Object.assign({fields: {}}, verdicts[r.pdf],
                                  {verdict: verdict, ts: new Date().toISOString()});
  // Advance only when this row is about to leave the visible list, so a
  // correction to an already-reviewed row keeps it on screen.
  const leaves = (filter === "todo");
  lastMarked = r.pdf;
  persist();
  if (leaves) {
    const vis = visible();
    if (vis.length) {
      const after = vis.find(x => ROWS.indexOf(x) > ROWS.findIndex(y => y.pdf === r.pdf));
      curPdf = (after || vis[vis.length - 1]).pdf;
    }
    saveUI();
  }
  render();
  toast(verdict + " — press u to reopen it");
}

/* ---- controls ----------------------------------------------------------- */
document.getElementById("link").onclick = async () => {
  try {
    handle = await window.showSaveFilePicker({suggestedName: "scrape_review.csv",
      types: [{description: "CSV", accept: {"text/csv": [".csv"]}}]});
    await persist(); toast("linked; decisions now save straight to that file");
  } catch (e) { toast("link cancelled"); }
};
document.getElementById("export").onclick = () => {
  const b = new Blob([csv()], {type: "text/csv"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(b); a.download = "scrape_review.csv"; a.click();
};
document.getElementById("import").onclick = () => document.getElementById("file").click();
document.getElementById("file").addEventListener("change", ev => {
  const f = ev.target.files && ev.target.files[0];
  if (!f) return;
  const rd = new FileReader();
  rd.onload = () => importCsv(String(rd.result));
  rd.readAsText(f);
  ev.target.value = "";
});
for (const [id, val] of [["f-all","all"],["f-todo","todo"],["f-done","done"],
                         ["f-ratio","ratio"],["f-crop","crop"]])
  document.getElementById(id).onclick = () => { filter = val; saveUI(); render(); };
document.getElementById("togidx").onclick = () => { showIdx = !showIdx; saveUI(); render(); };
const qbox = document.getElementById("q");
qbox.value = query;
qbox.addEventListener("input", () => { query = qbox.value; render(); });
qbox.addEventListener("keydown", e => {
  if (e.key === "Escape") { qbox.value = ""; query = ""; qbox.blur(); render(); }
  e.stopPropagation();
});
addEventListener("keydown", e => {
  if (e.target.tagName === "INPUT") { if (e.key === "Escape") e.target.blur(); return; }
  if (e.key === "1") mark("accepted");
  else if (e.key === "2") mark("flagged");
  else if (e.key === "3") mark("unusable");
  else if (e.key === "0") mark("");
  else if (e.key === "u") reopenLast();
  else if (e.key === "r") ackRatioAndStep();
  else if (e.key === "c") ackCropAndStep();
  else if (e.key === "/") { e.preventDefault(); qbox.focus(); qbox.select(); }
  else if (e.key === "e") { const i = document.querySelector("#side input"); if (i) { i.focus(); i.select(); } }
  else if (e.key === "ArrowRight" || e.key === "j") step(1);
  else if (e.key === "ArrowLeft" || e.key === "k") step(-1);
});
render();
</script>
"""

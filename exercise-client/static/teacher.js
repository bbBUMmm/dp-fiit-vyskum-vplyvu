/* teacher.js -- the teacher's dashboard.
 *
 * Runs the interactive part of the lesson: the teacher picks an activity and
 * it appears on every pupil's screen; responses come back aggregated, and the
 * teacher decides when to show the class result.
 *
 * What it shows about the class is technical: how many are connected, where in
 * the task sequence they are, whether the model is answering. Never a pupil's
 * prompt, and never a process or outcome measure during collection -- both are
 * promises in Appendix E. The researcher view is a separate switch on the
 * server and says so on screen.
 */
"use strict";

const $ = (id) => document.getElementById(id);
const { h } = window.Activity;
const TYPE_LABELS = window.Activity.TYPE_LABELS;
const PACK_LABELS = { informatika: "Informatika", matematika: "Matematika", fyzika: "Fyzika", vseobecne: "Všeobecné", vlastne: "Vytvorené počas hodiny" };

const D = { token: null, state: null, library: null, tab: null, kind: "poll", started: 0, offset: 0, lastQr: "" };
try { D.token = sessionStorage.getItem("teacher"); } catch (_) {}

async function api(path, body) {
  const opts = { method: body === undefined ? "GET" : "POST", headers: { "Content-Type": "application/json" } };
  if (D.token) opts.headers["X-Teacher"] = D.token;
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(path, opts);
  let data = {};
  try { data = await r.json(); } catch (_) {}
  if (r.status === 401) { showLogin(); throw new Error(data.error || "Prihlásenie vypršalo."); }
  if (!r.ok) throw new Error(data.error || `Chyba ${r.status}`);
  return data;
}

let toastTimer;
function toast(msg, bad) {
  const t = $("toast"); t.textContent = msg; t.className = "toast show" + (bad ? " bad" : "");
  clearTimeout(toastTimer); toastTimer = setTimeout(() => (t.className = "toast"), 3000);
}

// --------------------------------------------------------------- login
function showLogin() { $("app").hidden = true; $("login").hidden = false; $("pin").focus(); }
$("pin-go").addEventListener("click", async () => {
  $("pin-error").textContent = "";
  try {
    const r = await fetch("/api/teacher/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pin: $("pin").value.trim() }) });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || "Nesprávny PIN.");
    D.token = data.token;
    try { sessionStorage.setItem("teacher", D.token); } catch (_) {}
    await boot();
  } catch (e) { $("pin-error").textContent = e.message; }
});
$("pin").addEventListener("keydown", (e) => { if (e.key === "Enter") $("pin-go").click(); });

// --------------------------------------------------------------- state
async function refresh() {
  let st;
  try { st = await api("/api/teacher/state"); } catch (_) { return; }
  D.state = st;
  D.offset = st.lesson.now * 1000 - Date.now();
  renderHeader(st);
  renderJoin(st);
  renderClass(st);
  renderLive(st.live);
  markRunning(st.live);
  $("d-metrics").hidden = !st.researcherView;
}

function renderHeader(st) {
  const L = st.lesson;
  $("d-topic").textContent = L.topic;
  $("d-sub").textContent = `${PACK_LABELS[L.subject] || L.subject} · hodina ${L.session}` + (L.status ? ` · ${L.status}` : "");
  $("d-cond").textContent = L.condition;
  D.started = L.started * 1000;
  const seg = $("d-phase");
  if (!seg.childElementCount) {
    L.phases.forEach((p) => seg.appendChild(h("button", { type: "button", "data-p": p.id, "aria-pressed": "false",
      onclick: () => api("/api/teacher/phase", { phase: p.id }).then(refresh).catch((e) => toast(e.message, true)) }, p.label)));
  }
  seg.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.p === L.phase ? "true" : "false"));
}

function renderJoin(st) {
  const urls = st.join.urls;
  const main = urls[0];
  $("d-url").textContent = main;
  $("d-mode").textContent = st.join.local ? "len tento počítač" : "celá trieda (sieť)";
  $("d-join-note").textContent = st.join.local
    ? "Server počúva len na tomto počítači. Pre celú triedu ho spustite s --host 0.0.0.0."
    : "Žiaci otvoria adresu v prehliadači (počítač alebo mobil) a zadajú kód z obálky.";
  if (D.lastQr !== main) {
    D.lastQr = main;
    fetch("/api/teacher/qr.svg?text=" + encodeURIComponent(main), { headers: { "X-Teacher": D.token } })
      .then((r) => r.ok ? r.blob() : null)
      .then((b) => { if (b) $("d-qr").src = URL.createObjectURL(b); });
  }
  const box = $("d-urls"); box.innerHTML = "";
  if (urls.length > 1) urls.slice(1).forEach((u) => box.appendChild(h("span", { class: "chip chip-soft mono", text: u })));
}

function renderClass(st) {
  const c = st.counts;
  $("c-pupils").textContent = c.pupils;
  $("c-online").textContent = c.online;
  $("c-finished").textContent = c.finished;
  $("c-multi").textContent = c.multi_device;
  $("t-multi").classList.toggle("warn", c.multi_device > 0);
  const hist = $("d-hist"); hist.innerHTML = "";
  const max = Math.max(1, ...Object.values(st.progress));
  Object.entries(st.progress).forEach(([k, v]) => {
    if (k === "medzikrok" && !v) return;
    hist.appendChild(h("div", { class: "hist-row" }, h("span", { text: k }),
      h("div", { class: "result-track" }, h("i", { style: `width:${100 * v / max}%` })), h("b", { text: String(v) })));
  });
  const grid = $("d-grid"); grid.innerHTML = "";
  if (!st.grid.length) grid.appendChild(h("p", { class: "muted small", text: "Zatiaľ sa nikto neprihlásil." }));
  st.grid.forEach((p) => grid.appendChild(h("div", { class: "pupil " + (p.online ? "on" : "off"), title: p.online ? "online" : "offline" },
    h("b", { text: p.task }), h("span", { class: "mono", text: p.id }))));
  const hl = st.health;
  const rows = [["Udalosti v zázname", hl.events], ["Prompty", hl.prompts], ["Odpovede asistenta", hl.replies],
                ["Chyby poskytovateľa", hl.provider_errors], ["Zásahy strážcu (A)", hl.guard_violations],
                ["Medián odozvy", hl.latency_ms_median === null ? "—" : `${hl.latency_ms_median} ms`],
                ["Poskytovateľ", st.lesson.provider]];
  $("d-health").innerHTML = "";
  rows.forEach(([k, v]) => $("d-health").append(h("span", { class: "muted", text: k }), h("b", { text: String(v) })));
}

// -------------------------------------------------------------- live
function renderLive(live) {
  const body = $("l-body");
  if (!live) {
    $("h-live").textContent = "Žiadna aktivita práve nebeží";
    $("l-type").textContent = "Interaktívna časť";
    body.innerHTML = "";
    body.appendChild(h("p", { class: "live-empty" }, "Vyberte aktivitu nižšie a stlačte ", h("strong", { text: "Spustiť" }), ". Zobrazí sa naraz všetkým žiakom."));
    return;
  }
  const a = live.activity, r = live.results || {};
  $("h-live").textContent = a.title;
  $("l-type").textContent = TYPE_LABELS[a.type];
  body.innerHTML = "";
  body.appendChild(h("div", { class: "row", style: "margin-bottom:14px;align-items:flex-end" },
    h("div", {}, h("div", { class: "live-count", text: `${r.n || 0}` }), h("span", { class: "small muted", text: `odpovedí z ${r.viewers || 0} zobrazení` })),
    r.correct_share !== undefined ? h("div", { style: "margin-left:18px" }, h("div", { class: "live-count", text: `${Math.round(100 * r.correct_share)} %` }), h("span", { class: "small muted", text: "správne" })) : null,
    r.confidence_mean !== undefined ? h("div", { style: "margin-left:18px" }, h("div", { class: "live-count", text: `${Math.round(r.confidence_mean)} %` }), h("span", { class: "small muted", text: "priemerná istota" })) : null,
    h("span", { class: "spacer" }),
    live.revealed ? h("span", { class: "chip chip-good", text: "výsledky zverejnené" }) : null));
  if (a.question) body.appendChild(h("p", { class: "act-question", style: "font-size:1rem", text: a.question }));
  if (r.counts && r.options) {
    const total = r.counts.reduce((x, y) => x + y, 0) || 1;
    body.appendChild(h("div", { class: "result-bars" }, r.options.map((o, k) => h("div", { class: "result-row" + ((a.key === k || a.answer === k) ? " correct" : "") },
      h("div", {}, h("div", { class: "result-label" }, h("strong", { text: "ABCDEFGH"[k] }), h("span", { text: o })),
        h("div", { class: "result-track" }, h("i", { style: `width:${(100 * r.counts[k] / total).toFixed(1)}%` }))),
      h("div", { class: "result-n", text: String(r.counts[k]) })))));
  } else if (r.values && r.values.length) {
    body.appendChild(h("div", { class: "kv" },
      h("div", {}, h("b", { text: String(r.median ?? r.value_median) }), h("span", { text: "medián" })),
      r.min !== undefined ? h("div", {}, h("b", { text: `${r.min} – ${r.max}` }), h("span", { text: "rozpätie" })) : null,
      a.answer !== undefined ? h("div", {}, h("b", { text: String(a.answer) }), h("span", { text: "správna hodnota" })) : null,
      r.completed !== undefined ? h("div", {}, h("b", { text: String(r.completed) }), h("span", { text: "dokončili" })) : null));
  } else if (r.score_mean !== undefined) {
    body.appendChild(h("p", { text: `Priemerne ${Math.round(100 * r.score_mean)} % položiek na správnom mieste.` }));
  } else if (r.completed !== undefined) {
    body.appendChild(h("p", { text: `Aktivitu dokončilo ${r.completed} žiakov.` }));
  }
  if (r.texts && r.texts.length) {
    const box = h("div", { class: "texts", hidden: true }, r.texts.map((t) => h("p", { text: t })));
    const tg = h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: () => { box.hidden = !box.hidden; tg.textContent = box.hidden ? `Zobraziť odpovede (${r.texts.length}, anonymne)` : "Skryť odpovede"; } }, `Zobraziť odpovede (${r.texts.length}, anonymne)`);
    body.appendChild(h("div", { style: "margin-top:12px" }, tg, box));
  }
  body.appendChild(h("div", { class: "actions", style: "margin-top:18px" },
    live.revealed ? null : h("button", { class: "btn btn-good", type: "button", onclick: () => act("/api/teacher/activity/reveal") }, "Zverejniť výsledky triede"),
    h("button", { class: "btn btn-secondary", type: "button", onclick: () => preview(a) }, "Náhľad"),
    h("button", { class: "btn btn-danger", type: "button", onclick: () => act("/api/teacher/activity/close") }, "Ukončiť aktivitu")));
}

async function act(path, body) {
  try { await api(path, body || {}); await refresh(); } catch (e) { toast(e.message, true); }
}

// ------------------------------------------------------------- library
async function loadLibrary() {
  D.library = await api("/api/teacher/library");
  const packs = D.library.packs;
  if (!D.tab || !packs.some((p) => p.pack === D.tab)) {
    const own = packs.find((p) => p.pack === D.library.subject);
    D.tab = own ? own.pack : (packs[0] && packs[0].pack);
  }
  renderTabs(); renderLibrary();
}
function renderTabs() {
  const tabs = $("d-tabs"); tabs.innerHTML = "";
  D.library.packs.forEach((p) => tabs.appendChild(h("button", { type: "button", role: "tab", "aria-selected": p.pack === D.tab ? "true" : "false",
    onclick: () => { D.tab = p.pack; renderTabs(); renderLibrary(); } }, `${PACK_LABELS[p.pack] || p.title} (${p.activities.length})`)));
}
function renderLibrary() {
  const lib = $("d-lib"); lib.innerHTML = "";
  const pack = D.library.packs.find((p) => p.pack === D.tab);
  if (!pack) { lib.appendChild(h("p", { class: "muted", text: "Žiadne aktivity." })); return; }
  const phases = Object.fromEntries(D.library.phases.map((p) => [p.id, p.label]));
  pack.activities.forEach((a) => lib.appendChild(h("article", { class: "lib-card", "data-id": a.id },
    h("div", { class: "row" }, h("span", { class: "chip chip-accent", text: TYPE_LABELS[a.type] }), a.phase ? h("span", { class: "chip chip-soft", text: phases[a.phase] || a.phase }) : null),
    h("strong", { text: a.title }),
    h("p", { class: "q", text: a.question || a.intro || "" }),
    a.note ? h("p", { class: "small", style: "color:var(--warn)", text: "⚠ " + a.note }) : null,
    h("div", { class: "row" },
      h("button", { class: "btn btn-primary btn-sm", type: "button", onclick: () => act("/api/teacher/activity/start", { id: a.id }) }, "Spustiť"),
      h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: () => preview(a) }, "Náhľad")))));
  markRunning(D.state && D.state.live);
}
function markRunning(live) {
  document.querySelectorAll(".lib-card").forEach((c) => c.classList.toggle("running", !!live && c.dataset.id === live.id));
}

// -------------------------------------------------------------- preview
let previewHandle = null;
function preview(a) {
  $("p-title").textContent = a.title;
  const view = { activity: Object.assign({}, a, { display: a.type === "order" ? a.items.map((_, k) => k).reverse() : undefined }), version: 0, revealed: false, mine: null };
  previewHandle = window.Activity.render($("p-body"), view, {
    submit: () => Promise.resolve({ mine: null }).then((r) => { toast("Náhľad — odpoveď sa neodosiela."); return r; }),
  });
  $("preview-layer").hidden = false;
}
$("p-close").addEventListener("click", () => { if (previewHandle && previewHandle.destroy) previewHandle.destroy(); $("preview-layer").hidden = true; $("p-body").innerHTML = ""; });

// ---------------------------------------------------------- new activity
$("b-new").addEventListener("click", () => { $("d-create").hidden = false; buildForm(); $("d-create").scrollIntoView({ behavior: "smooth" }); });
$("b-create-close").addEventListener("click", () => { $("d-create").hidden = true; });
document.querySelectorAll("#n-kind button").forEach((b) => b.addEventListener("click", () => {
  D.kind = b.dataset.k;
  document.querySelectorAll("#n-kind button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
  buildForm();
}));

function buildForm() {
  const f = $("n-form"); f.innerHTML = ""; $("n-error").textContent = "";
  const field = (label, el) => h("div", {}, h("label", { text: label }), el);
  if (D.kind === "json") {
    f.appendChild(field("Definícia aktivity (JSON)", h("textarea", { id: "n-json", rows: "12", class: "mono", spellcheck: "false",
      placeholder: '{\n  "type": "poll",\n  "title": "Rýchla otázka",\n  "question": "…",\n  "options": ["A", "B"],\n  "key": 0,\n  "confidence": true\n}' })));
    f.appendChild(h("p", { class: "fineprint", text: "Typy: poll, predict, order, animation, handson, reflect. Widgety: binary-search, search-race, guess-number, interest, circuit, frames. Formát je opísaný v README klienta." }));
    return;
  }
  f.appendChild(field("Názov (nepovinné)", h("input", { id: "n-title", type: "text", maxlength: "120", placeholder: D.kind === "reflect" ? "Výstupný lístok" : "Rýchla otázka" })));
  f.appendChild(field(D.kind === "reflect" ? "Otázka na zamyslenie" : "Otázka", h("textarea", { id: "n-q", rows: "2", placeholder: D.kind === "reflect" ? "Čo ti dnes ešte nie je jasné?" : "Napíšte otázku…" })));
  if (D.kind === "poll") {
    const list = h("div", { id: "n-opts" });
    const add = () => {
      const k = list.childElementCount;
      if (k >= 6) return;
      list.appendChild(h("div", { class: "opt-row" },
        h("input", { type: "radio", name: "n-key", value: String(k), "aria-label": "Správna možnosť" }),
        h("input", { type: "text", placeholder: `Možnosť ${"ABCDEF"[k]}`, "data-opt": "1" }),
        h("span", { class: "small muted", text: "ABCDEF"[k] })));
    };
    add(); add(); add();
    f.appendChild(h("div", {}, h("label", { text: "Možnosti (kolieskom označte správnu, ak nejaká je)" }), list,
      h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: add }, "+ možnosť")));
  }
  if (D.kind === "number") {
    f.appendChild(h("div", { class: "row" },
      field("Správna hodnota (nepovinné)", h("input", { id: "n-ans", type: "number", step: "any" })),
      field("Tolerancia", h("input", { id: "n-tol", type: "number", step: "any", value: "0", min: "0" }))));
  }
  f.appendChild(h("label", { class: "row", style: "font-weight:600" }, h("input", { id: "n-conf", type: "checkbox", checked: true }), D.kind === "reflect" ? "Pýtať sa aj „Nakoľko téme rozumieš?“ (0–100 %)" : "Pýtať sa na istotu (0–100 %)"));
}

function readForm() {
  if (D.kind === "json") {
    try { return JSON.parse($("n-json").value); } catch (e) { throw new Error("JSON sa nedá prečítať: " + e.message); }
  }
  const q = ($("n-q").value || "").trim();
  const title = ($("n-title").value || "").trim();
  const conf = $("n-conf").checked;
  if (!q) throw new Error("Napíšte otázku.");
  if (D.kind === "poll") {
    const opts = Array.from(document.querySelectorAll("[data-opt]")).map((x) => x.value.trim());
    const keyEl = document.querySelector("input[name=n-key]:checked");
    const filled = opts.map((o, k) => [o, k]).filter(([o]) => o);
    if (filled.length < 2) throw new Error("Zadajte aspoň dve možnosti.");
    const def = { type: "poll", title: title || "Rýchla otázka", question: q, options: filled.map(([o]) => o), confidence: conf, phase: currentPhase() };
    if (keyEl) { const k = filled.findIndex(([, idx]) => idx === Number(keyEl.value)); if (k >= 0) def.key = k; }
    return def;
  }
  if (D.kind === "number") {
    const def = { type: "predict", title: title || "Predpoveď", question: q, input: { kind: "number", tolerance: Number($("n-tol").value || 0) }, confidence: conf, phase: currentPhase() };
    if ($("n-ans").value !== "") def.answer = Number($("n-ans").value);
    return def;
  }
  return { type: "reflect", title: title || "Reflexia", question: q, confidence: conf, phase: currentPhase() };
}
const currentPhase = () => (D.state ? D.state.lesson.phase : undefined);

async function save(start) {
  $("n-error").textContent = "";
  let def;
  try { def = readForm(); } catch (e) { $("n-error").textContent = e.message; return; }
  try {
    await api("/api/teacher/activity/create", { definition: def, start });
    toast(start ? "Aktivita spustená." : "Aktivita uložená do knižnice.");
    D.tab = "vlastne";
    $("d-create").hidden = true;
    await loadLibrary(); await refresh();
  } catch (e) { $("n-error").textContent = e.message; }
}
$("n-save").addEventListener("click", () => save(false));
$("n-save-start").addEventListener("click", () => save(true));

// -------------------------------------------------------------- metrics
$("b-metrics").addEventListener("click", async () => {
  try {
    const m = await api("/api/teacher/metrics");
    const body = $("m-body"); body.innerHTML = "";
    const cols = ["pseudonym", "n_prompts", "peqi", "offload_rate", "abhr", "t_first_prompt_median_s", "help_with_own_draft_rate",
                  "copied_answer_rate", "clicks", "confidence_mean", "lesson_calibration_bias", "active_ratio", "activity_participation", "engagement_index"];
    const fmt = (v) => (v === null || v === undefined ? "—" : typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(2)) : String(v).slice(0, 8));
    body.appendChild(h("div", { class: "table-wrap" }, h("table", { class: "data" },
      h("thead", {}, h("tr", {}, cols.map((c) => h("th", { text: c })))),
      h("tbody", {}, m.rows.map((r) => h("tr", {}, cols.map((c) => h("td", { text: fmt(r[c]) }))))))));
  } catch (e) { toast(e.message, true); }
});
$("b-export").addEventListener("click", async (e) => {
  e.preventDefault();
  try {
    const r = await fetch("/api/teacher/export.csv", { headers: { "X-Teacher": D.token } });
    if (!r.ok) throw new Error("Export nie je dostupný.");
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a"); a.href = url; a.download = "metriky.csv"; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  } catch (err) { toast(err.message, true); }
});

// ---------------------------------------------------------------- timer
setInterval(() => {
  if (!D.started) return;
  const s = Math.max(0, Math.floor((Date.now() + D.offset - D.started) / 1000));
  const hh = Math.floor(s / 3600), mm = Math.floor((s % 3600) / 60), ss = s % 60;
  $("d-timer").textContent = (hh ? hh + ":" : "") + String(mm).padStart(2, "0") + ":" + String(ss).padStart(2, "0");
}, 1000);

// ----------------------------------------------------------------- boot
let loop = null;
async function boot() {
  await refresh();
  if (!D.state) { showLogin(); return; }
  $("login").hidden = true; $("app").hidden = false;
  await loadLibrary();
  if (!loop) loop = setInterval(refresh, 2000);
}
(async () => { if (D.token) { try { await boot(); return; } catch (_) {} } showLogin(); })();

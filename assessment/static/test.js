// test.js -- the pupil-facing test client.
//
// Three things here are measurements and not interface:
//
//   * blur_seconds. The time the test window spent not focused while an item was
//     open. It is the only trace a tab switch leaves, and tab switching is the
//     cheapest way to look an answer up.
//   * paste_events. A pasted free-text answer was not written.
//   * revisions. How many times the pupil changed an answer before submitting,
//     which separates a considered change of mind from a first guess. For a
//     choice that is every change after the first pick; for text it is every
//     burst of deleting. (The first version counted every keystroke of a text
//     answer as a "revision".)
//
// All three are recorded, none is shown to the pupil, and none is ever treated
// as proof on its own -- integrity.py needs two independent families.
//
// The confidence slider and the scales have NO default value. A slider that
// starts at 50 records 50 for every pupil who never touched it, and a
// calibration measure built on that is measuring the default.
//
// The client gives NO feedback about correctness. This test sits between two
// measurements of learning; telling a pupil the answer would make it a third.
//
// Consent is asked after the code and before the first item (consent.js, the
// lesson's component). The server writes nothing of the sitting until the
// answer is yes; either answer leads to the same test.
//
// The test section (runner.py --test): the topic tests from testy/*.txt. Items
// come in parts (questionnaire, self-efficacy, closed, semi-open, open, a text
// with questions); each part opens with its instructions. Every closed item
// looks the same -- checkboxes and the same sentence -- whether one answer is
// correct or several (the supervisor's note: the page does not say which).
// "Neviem" records an explicit "I don't know" instead of forcing a guess.
"use strict";

let token = null, current = null, total = 0, answered = 0, finished = false, consentView = null;
let blurStart = null, blurAccum = 0, pastes = 0, revisions = 0;
let choiceChanges = 0, lastLen = 0, lastDeleteAt = 0, jolTouched = false, scaleTouched = false;
let busy = false, storedCode = null, connIssue = false;
let formInfo = null, lastPart = null;

const el = (id) => document.getElementById(id);
function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat()) if (c !== null && c !== undefined && c !== false) e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  return e;
}
const LETTERS = "ABCDEFGH";
const KNOWLEDGE = ["closed", "semi", "open"];

window.addEventListener("blur", () => { blurStart = blurStart || Date.now(); });
window.addEventListener("focus", () => {
  if (blurStart) { blurAccum += (Date.now() - blurStart) / 1000; blurStart = null; }
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) { blurStart = blurStart || Date.now(); }
  else if (blurStart) { blurAccum += (Date.now() - blurStart) / 1000; blurStart = null; }
});

function banner(msg) {
  const b = el("banner");
  b.textContent = msg || "";
  b.classList.toggle("show", !!msg);
}

async function post(path, body, retries = 3) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["X-Sitting"] = token;
  for (let attempt = 0; ; attempt++) {
    try {
      const r = await fetch(path, { method: "POST", headers, body: JSON.stringify(body || {}) });
      let data = {};
      try { data = await r.json(); } catch (_) {}
      if (connIssue) { banner(""); connIssue = false; }
      return { ok: r.ok, status: r.status, data };
    } catch (e) {
      // the school Wi-Fi dropped: keep the answer on screen and try again
      connIssue = true;
      banner("Spojenie sa prerušilo — skúšam znova… Odpoveď sa nestratí.");
      if (attempt >= retries) return { ok: false, status: 0, data: { error: "Server nie je dostupný. Zavolaj vyučujúceho." } };
      await new Promise((res) => setTimeout(res, 1500 * (attempt + 1)));
    }
  }
}

const SUBJECT = { fyzika: "Fyzika", matematika: "Matematika", informatika: "Informatika" };
const TEST_NAME = { T1: "vstupný test", T3: "test po hodine", T4: "odložený test" };

async function boot() {
  let info;
  try { info = await (await fetch("/api/info")).json(); }
  catch (_) { el("card").textContent = "Server testu nie je dostupný. Zavolaj vyučujúceho."; return; }
  if (info.section === "testy" && info.form) {
    formInfo = info.form;
    document.body.classList.add("testy");
    const subj = SUBJECT[formInfo.subject] || "";
    const name = TEST_NAME[formInfo.test] || "dotazník";
    el("title").textContent = subj ? `${subj} · ${formInfo.topicTitle}` : (formInfo.titleLines[0] || info.title);
    el("sub").textContent = `${subj ? name + " · " : ""}${info.items} položiek · približne ${Math.round(info.minutes)} minút`;
    el("section").hidden = false;
    document.querySelector(".logo").textContent = "T";   // the test section, not the AI lesson
    document.title = subj ? `Testy · ${subj} · ${name}` : "Testy · dotazník";
  } else {
    el("title").textContent = info.title;
    el("sub").textContent = `${info.items} položiek · stretnutie ${info.session}`;
    document.title = info.title;
  }
  total = info.items;
  askForCode(info.codeFormat);
}

async function sendConsent(choice) {
  const r = await post("/api/consent", choice ? { choice } : {});
  if (!r.ok) throw new Error(r.data.error || "Nepodarilo sa uložiť. Skús to znova.");
  consentView = r.data;
  return consentView;
}

el("consent-btn").addEventListener("click", async () => {
  try { await sendConsent(null); } catch (_) { /* show what we have */ }
  if (consentView) Consent.manage({ view: consentView, send: sendConsent });
});

function askForCode(fmt, message) {
  token = null;
  finished = false;
  lastPart = null;
  el("consent-btn").hidden = true;
  const input = h("input", { type: "text", id: "code", class: "code", autocomplete: "off", autocapitalize: "characters",
                             spellcheck: "false", placeholder: fmt || "GY-XXXXX-X", maxlength: "20", "aria-label": "Kód z obálky" });
  const err = h("div", { class: "err", id: "cerr", role: "alert", text: message || "" });
  const go = h("button", { class: "btn btn-block", id: "go", type: "button" }, "Začať");
  const intro = formInfo && formInfo.instructions
    ? h("div", { class: "pokyny" }, h("div", { class: "eyebrow", text: "Pokyny" }), multiline(formInfo.instructions))
    : null;
  // replaceChildren() would turn a null into the text "null": filter first
  el("card").replaceChildren(...[
    h("div", { class: "eyebrow", text: "Prihlásenie" }),
    h("p", { class: "stem", text: "Zadaj kód z obálky." }),
    input, err, go,
    intro,
    h("p", { class: "note", text: "Kód nie je tvoje meno. Po zadaní kódu ti ukážeme, čo sa zaznamenáva, a spýtame sa ťa na súhlas. Výsledok nemá vplyv na známku a kedykoľvek môžeš prestať bez následku." })].filter(Boolean));
  go.onclick = start;
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") start(); });
  input.focus();
}

async function start() {
  const code = el("code").value;
  el("go").disabled = true;
  const { ok, data } = await post("/api/start", { code });
  if (!ok) {
    el("cerr").textContent = data.error || "Nepodarilo sa začať.";
    el("go").disabled = false;
    el("code").select();
    return;
  }
  storedCode = code;
  token = data.token;
  total = data.total;
  consentView = data.consent || null;
  el("consent-btn").hidden = false;
  if (consentView && (consentView.state === "pending" || consentView.state === "none")) {
    await Consent.ask({ view: consentView, send: sendConsent });
  }
  if (data.resumed) banner(`Pokračuješ tam, kde si skončil/a (${data.answered} z ${data.total} položiek je uložených).`);
  nextItem();
}

async function nextItem() {
  blurAccum = 0; pastes = 0; revisions = 0; blurStart = document.hidden ? Date.now() : null;
  choiceChanges = 0; lastLen = 0; lastDeleteAt = 0; jolTouched = false; scaleTouched = false;
  const r = await post("/api/item", {});
  if (r.status === 401) return askForCode(null, "Relácia vypršala. Zadaj kód znova — tvoje odpovede sú uložené.");
  if (!r.ok) { el("card").replaceChildren(h("p", { class: "err", text: r.data.error || "Chyba servera." }), h("button", { class: "btn", type: "button", onclick: nextItem }, "Skúsiť znova")); return; }
  const data = r.data;
  if (data.done) return finish(data);
  current = data.item;
  const part = current.part;
  if (part && part.key !== lastPart) {
    lastPart = part.key;
    return partIntro(part, data);
  }
  render(data);
}

// ---------------------------------------------------------------- helpers
// Text from a .txt file is hard-wrapped at about 74 characters for paper. On a
// screen (and a phone) prose is reflowed into paragraphs; what is aligned on
// purpose -- code, pseudocode, tables -- stays as it is, in monospace. A line is
// "aligned" when it is indented by 4+ spaces, or indented and has columns.
// Bullets, "(1)" sub-questions and blank lines start a new paragraph.
function reflow(text, codeClass) {
  const out = [];
  let para = null, pre = null;
  const endPara = () => { if (para) { out.push(h("p", { class: "rf-p", text: para.join(" ") })); para = null; } };
  const endPre = () => { if (pre) { out.push(h("pre", { class: codeClass || "code", text: pre.join("\n") })); pre = null; } };
  for (const raw of (text || "").replace(/\r/g, "").split("\n")) {
    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) { endPara(); endPre(); continue; }
    const indent = line.match(/^ */)[0].length;
    const columns = /\S {2,}\S/.test(line.trim());
    if (indent >= 4 || (indent >= 1 && columns)) {
      endPara();
      (pre = pre || []).push(line.replace(/^ {1,4}/, ""));
      continue;
    }
    endPre();
    const t = line.trim();
    if (!para || /^(•|–|-|\(\d+\)|[a-h]\))\s/.test(t)) { endPara(); para = [t]; }
    else para.push(t);
  }
  endPara(); endPre();
  return out;
}

function multiline(text) {
  return h("div", { class: "multiline" }, reflow(text));
}

function stemBlock(text) {
  return h("div", { class: "stem" }, reflow(text));
}

function partIntro(part, data) {
  setProgress(data.index - 1);
  const knowledge = KNOWLEDGE.includes(current.kind) || part.kind === "text";
  const go = h("button", { class: "btn btn-block", type: "button" }, "Začať");
  go.onclick = () => render(data);
  el("card").replaceChildren(...[
    h("div", { class: "eyebrow", text: knowledge ? "Časť testu" : "Dotazník" }),
    h("h2", { class: "part-title", text: part.title }),
    multiline(part.instructions),
    knowledge && formInfo && formInfo.conventions
      ? h("details", { class: "dohody", open: true }, h("summary", { text: "Dohody platné v celom teste" }), h("div", { class: "conv" }, reflow(formInfo.conventions)))
      : null,
    go].filter(Boolean));
  go.focus();
}

function setProgress(done) {
  el("bar").style.width = `${total ? (100 * done / total) : 0}%`;
  el("progtext").textContent = `${done} / ${total}`;
}

// ---------------------------------------------------------------- render
function render(d) {
  const it = d.item;
  setProgress(d.index - 1);
  const card = el("card");
  const knowledge = KNOWLEDGE.includes(it.kind);
  const label = it.part ? `${it.part.title.split(" (")[0]} · položka ${d.index} z ${d.total}` : `Položka ${d.index} z ${d.total}`;
  const parts = [h("div", { class: "eyebrow", text: label })];

  if (it.stimulus && it.stimulus.text) {
    parts.push(h("details", { class: "stim", open: true },
      h("summary", { text: it.stimulus.title ? `Text: ${it.stimulus.title}` : "Text" }),
      h("div", { class: "stim-text" }, reflow(it.stimulus.text, "table"))));
  }
  parts.push(it.part ? stemBlock(it.stem) : h("p", { class: "stem", text: it.stem }));

  const choiceOpt = (label, value, type, mark) => {
    const input = h("input", { type, name: "ans", value: String(value) });
    const lab = h("label", { class: "opt" }, input, h("span", { class: "mark", text: mark }), label === null ? null : h("span", { text: label }));
    input.addEventListener("change", () => {
      choiceChanges++;
      revisions = Math.max(0, choiceChanges - 1);
      scaleTouched = true;
      document.querySelectorAll(".opt").forEach((l) => l.classList.toggle("sel", l.querySelector("input").checked));
    });
    return lab;
  };

  if (["mc4", "mc3"].includes(it.format) || (it.format === "choice" && !it.part)) {
    parts.push(h("div", { role: "radiogroup" }, it.options.map((o, i) => choiceOpt(o, i, "radio", LETTERS[i]))));
  } else if (it.format === "choice") {
    parts.push(h("div", { role: "radiogroup" }, it.options.map((o, i) => choiceOpt(o, i, "radio", LETTERS[i].toLowerCase()))));
  } else if (it.format === "mr") {
    // the same sentence for every closed item: one correct answer or several
    parts.push(h("p", { class: "note mr-note", text: "Označ všetky správne odpovede." }));
    parts.push(h("div", { role: "group" }, it.options.map((o, i) => choiceOpt(o, i, "checkbox", LETTERS[i].toLowerCase()))));
  } else if (it.format === "multi") {
    parts.push(h("div", { role: "group" }, it.options.map((o, i) => choiceOpt(o, i, "checkbox", it.part ? LETTERS[i].toLowerCase() : "✓"))));
    // deliberately silent about HOW MANY are correct (the supervisor's note)
    parts.push(h("p", { class: "note", style: "margin-top:4px", text: it.part ? "Môžeš označiť viac možností." : "Označ všetky správne možnosti." }));
  } else if (it.format === "likert5" || it.format === "likert7") {
    const n = it.format === "likert5" ? 5 : 7;
    parts.push(h("div", { class: "likert", role: "radiogroup" }, Array.from({ length: n }, (_, i) => choiceOpt(null, i + 1, "radio", String(i + 1)))));
    parts.push(h("div", { class: "scale-ends" }, h("span", { text: "1 = vôbec nesúhlasím" }), h("span", { text: `${n} = úplne súhlasím` })));
  } else if (it.format === "scale") {
    const s = it.scale;
    const values = [];
    for (let v = s.min; v <= s.max; v += s.step) values.push(v);
    parts.push(h("div", { class: "likert" + (values.length > 7 ? " wide" : ""), role: "radiogroup", "aria-label": `${s.left} až ${s.right}` },
      values.map((v) => choiceOpt(null, v, "radio", String(v)))));
    parts.push(h("div", { class: "scale-ends" }, h("span", { text: `${s.min} = ${s.left}` }), h("span", { text: `${s.max} = ${s.right}` })));
  } else if (it.format === "scale0_10" || it.format === "scale0_100") {
    const max = it.format === "scale0_10" ? 10 : 100;
    const out = h("span", { class: "jolval", text: "—" });
    const range = h("input", { type: "range", id: "free", min: "0", max: String(max), step: max === 10 ? "1" : "5", value: String(max / 2), class: "unset", "aria-label": "Hodnota na škále" });
    const touch = () => { scaleTouched = true; range.classList.remove("unset"); out.textContent = range.value; };
    range.addEventListener("input", touch);
    range.addEventListener("change", touch);
    parts.push(h("div", {}, h("div", { style: "text-align:center;font-size:1.3rem;margin-bottom:4px" }, out), range,
      h("div", { class: "scale-ends" }, h("span", { text: "0 = vôbec nie" }), h("span", { text: `${max} = úplne áno` }))));
  } else if (it.format === "numeric" || it.format === "number") {
    parts.push(h("input", { type: "text", id: "free", inputmode: it.format === "number" ? "numeric" : "decimal", autocomplete: "off", "aria-label": "Tvoja odpoveď",
                            placeholder: it.scale && it.scale.number ? `číslo ${it.scale.min} – ${it.scale.max}` : "" }));
  } else if (it.format === "short") {
    parts.push(h("div", { class: "fields" }, (it.fields || []).map((f, i) => {
      const id = `fld${i}`;
      return h("div", { class: "fld" },
        h("label", { for: id, text: f.label || "Odpoveď" }),
        h("input", { type: "text", id, class: "fld-in", autocomplete: "off", spellcheck: "false",
                     inputmode: f.kind === "number" ? "decimal" : "text", "aria-label": f.label || "Odpoveď" }),
        h("span", { class: "unit", text: f.unit || "" }));
    })));
  } else {
    parts.push(h("textarea", { id: "free", placeholder: it.rubric_hint || "", "aria-label": "Tvoja odpoveď" }));
  }

  if (it.jol) {
    const out = h("span", { class: "jolval", id: "jolv", text: "—" });
    const range = h("input", { type: "range", id: "jolr", min: "0", max: "100", step: "5", value: "50", class: "unset", "aria-label": "Istota v percentách" });
    const touch = () => { jolTouched = true; range.classList.remove("unset"); out.textContent = range.value + " %"; };
    range.addEventListener("input", touch);
    range.addEventListener("change", touch);
    parts.push(h("div", { class: "jol" },
      h("label", { for: "jolr" }, "Nakoľko si si istý/á, že tvoja odpoveď je správna? ", out),
      range, h("div", { class: "scale-ends" }, h("span", { text: "0 % určite nie" }), h("span", { text: "100 % určite áno" }))));
  }
  if (knowledge && formInfo && formInfo.conventions) {
    parts.push(h("details", { class: "dohody" }, h("summary", { text: "Dohody platné v celom teste" }), h("div", { class: "conv" }, reflow(formInfo.conventions))));
  }
  parts.push(h("div", { class: "err", id: "aerr", role: "alert" }));
  const next = h("button", { class: "btn", id: "next", type: "button" }, d.index === d.total ? "Dokončiť" : "Ďalej");
  const row = [next];
  if (it.skip) {
    const skip = h("button", { class: "btn btn-quiet", id: "skip", type: "button" }, knowledge ? "Neviem" : "Nechcem odpovedať");
    skip.onclick = () => submit(true);
    row.push(skip);
  }
  parts.push(h("div", { class: "actions" }, row));
  card.replaceChildren(...parts);

  const free = el("free");
  const texts = free && free.type !== "range" ? [free] : [...document.querySelectorAll(".fld-in")];
  for (const t of texts) {
    t.addEventListener("paste", () => { pastes++; });
    t.addEventListener("input", () => {
      const len = t.value.length;
      if (len < lastLen) {                       // a deletion; bursts > 1 s apart count once each
        const now = Date.now();
        if (now - lastDeleteAt > 1000) revisions++;
        lastDeleteAt = now;
      }
      lastLen = len;
    });
    if (t.tagName === "INPUT") t.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
  }
  if (texts.length) texts[0].focus();
  next.onclick = () => submit(false);
}

async function submit(skip) {
  if (busy) return;
  const err = el("aerr");
  let raw = null;
  const it = current;
  if (skip) {
    raw = "?";
  } else if (it.format === "short") {
    const vals = [...document.querySelectorAll(".fld-in")].map((x) => x.value.trim());
    if (!vals.some((v) => v)) { err.textContent = "Vyplň aspoň jedno políčko, alebo zvoľ „Neviem“."; return; }
    raw = JSON.stringify(vals);
  } else {
    const free = el("free");
    if (free) {
      if (free.type === "range" && !scaleTouched) { err.textContent = "Posuň posuvník na hodnotu, ktorá platí pre teba."; return; }
      raw = free.value;
    } else {
      raw = [...document.querySelectorAll('input[name="ans"]:checked')].map((x) => x.value).join(",");
    }
  }
  if (raw === null || raw.trim() === "") {
    err.textContent = it.skip
      ? (KNOWLEDGE.includes(it.kind) ? "Odpoveď je prázdna. Ak nevieš, stlač „Neviem“." : "Vyber odpoveď, alebo stlač „Nechcem odpovedať“.")
      : "Odpoveď je prázdna. Ak nevieš, napíš „neviem“ — aj to je odpoveď.";
    return;
  }
  const jr = el("jolr");
  if (jr && !jolTouched && !skip) { err.textContent = "Ešte nastav, nakoľko si si istý/á svojou odpoveďou."; return; }
  busy = true;
  el("next").disabled = true;
  if (el("skip")) el("skip").disabled = true;
  if (blurStart) { blurAccum += (Date.now() - blurStart) / 1000; blurStart = null; }
  const r = await post("/api/answer", {
    item_id: it.id, raw,
    jol: jr && !skip ? Number(jr.value) : null,
    paste_events: pastes, blur_seconds: blurAccum, revisions,
  });
  busy = false;
  if (r.status === 401) return askForCode(null, "Relácia vypršala. Zadaj kód znova — tvoje odpovede sú uložené.");
  if (!r.ok) {
    err.textContent = r.data.error || "Odpoveď sa nepodarilo uložiť. Skús znova.";
    el("next").disabled = false;
    if (el("skip")) el("skip").disabled = false;
    if (r.status === 400 && /nie je na rade/.test(r.data.error || "")) setTimeout(nextItem, 800);
    return;
  }
  answered++;
  nextItem();
}

function finish(d) {
  setProgress(total);
  finished = true;          // the token stays: consent can still be withdrawn here
  el("card").replaceChildren(
    h("div", { class: "done" },
      h("div", { class: "big", "aria-hidden": "true", text: "✓" }),
      h("p", { class: "stem", text: `Hotovo. Odpovedal/a si na ${d.answered} položiek.` }),
      h("p", { class: "note", text: "Výsledok sa nezobrazuje: tento test meria, čo si sa naučil/a, a ukázať správne odpovede by z neho urobilo ďalšiu hodinu. Celé zadania aj odpovede dostaneš po skončení štúdie." }),
      h("p", { class: "note", text: "Môžeš zavrieť okno." })));
}

// heartbeat: an open test is not "abandoned" while the pupil is on it, so the
// one-code-one-sitting lock holds; a dead laptop stops beating and the pupil
// can continue on another machine after two minutes
setInterval(() => { if (token && !finished) post("/api/ping", {}, 0).catch(() => {}); }, 30000);

boot();

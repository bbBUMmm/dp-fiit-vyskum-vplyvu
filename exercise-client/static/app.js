/* app.js -- the pupil-facing client.
 *
 * Several things here matter for the research rather than for the user:
 *
 *   1. The first keystroke on a task is reported to the server. Without it,
 *      "time to first prompt" cannot distinguish a pupil who read the task for
 *      ninety seconds from one who never looked at it.
 *   2. The assistant panel is hidden in condition K, but that is cosmetic --
 *      the server refuses the endpoint as well, and a request from a pupil who
 *      found it anyway is logged as a protocol deviation.
 *   3. Copying out of the assistant panel and pasting into the answer are
 *      reported (counts and lengths only), because "does the pupil just copy the
 *      tool's answer" is one of the questions chapter 5 asks.
 *   4. Interaction counters -- clicks, keystrokes, focus losses, and whether the
 *      time was active, idle or spent in another window -- are sent every 30 s.
 *      They are the raw material of the engagement measures. No content.
 *   5. The self-assessment asks for a confidence, and the slider has no default:
 *      a pre-set 50 % would be recorded as a judgement nobody made.
 *   6. Consent is asked after the code and before the first task (consent.js).
 *      The server writes nothing about the pupil until the answer is yes; the
 *      app answers both choices with the same message and runs the same way.
 *
 * Nothing here reads the experimental condition except to decide whether the
 * assistant panel exists and what "Ukázať riešenie" does, as before.
 */
"use strict";

const $ = (id) => document.getElementById(id);
const { h } = window.Activity;

const store = {
  get(k) { try { return sessionStorage.getItem(k); } catch (_) { return null; } },
  set(k, v) { try { sessionStorage.setItem(k, v); } catch (_) {} },
  del(k) { try { sessionStorage.removeItem(k); } catch (_) {} },
};
function deviceId() {
  try {
    let d = localStorage.getItem("device");
    if (!d) { d = Math.random().toString(36).slice(2, 10); localStorage.setItem("device", d); }
    return d;
  } catch (_) { return "nostorage"; }
}

const S = {
  token: store.get("token"),
  code: store.get("code"),
  config: null,
  task: null,
  typed: false,
  pastedFromAssistant: false,
  self: { choice: null },
  asking: false,
  activity: { id: null, version: null, revealed: null, view: null, handle: null, shownAt: 0, msVisible: 0, open: false },
  online: true,
  consent: null,
};

// ------------------------------------------------------------------ network
class ApiError extends Error { constructor(msg, status) { super(msg); this.status = status; } }

async function api(path, body, opts = {}) {
  const method = opts.method || (body === undefined ? "GET" : "POST");
  const headers = { "Content-Type": "application/json" };
  if (S.token) headers["X-Token"] = S.token;
  let r;
  try {
    r = await fetch(path, { method, headers, body: method === "POST" ? JSON.stringify(body || {}) : undefined, keepalive: !!opts.keepalive });
  } catch (e) {
    setOnline(false);
    throw new ApiError("Spojenie so serverom sa prerušilo. Skús to o chvíľu znova.", 0);
  }
  setOnline(true);
  let data = {};
  try { data = await r.json(); } catch (_) { /* non-JSON error page */ }
  if (r.status === 401 && !opts.noRelogin && S.code) {
    // the server restarted or the session expired: log in again with the same
    // code and repeat the request once. A restart forgets a "no" (it was never
    // written), so the pupil may be asked again.
    await login(S.code, true);
    if (S.consent && S.consent.state === "pending") ensureConsent();
    return api(path, body, Object.assign({}, opts, { noRelogin: true }));
  }
  if (!r.ok) throw new ApiError(data.error || `Chyba servera (${r.status})`, r.status);
  return data;
}

function setOnline(on) {
  if (S.online === on) return;
  S.online = on;
  $("net").classList.toggle("off", !on);
  $("net").textContent = on ? "online" : "offline";
  if (!on) toast("Spojenie sa prerušilo — pokúšam sa znova…", true);
}

let toastTimer = null;
function toast(msg, bad) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "toast show" + (bad ? " bad" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.className = "toast"; }, 3200);
}

// -------------------------------------------------------------------- login
async function login(code, silent) {
  const r = await fetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" },
                                        body: JSON.stringify({ code, device: deviceId() }) });
  let data = {};
  try { data = await r.json(); } catch (_) {}
  if (!r.ok) {
    if (silent) { logoutLocal(); throw new ApiError(data.error || "Prihlásenie zlyhalo.", r.status); }
    throw new ApiError(data.error || "Prihlásenie zlyhalo.", r.status);
  }
  S.token = data.token; S.code = code;
  S.consent = data.consent || null;
  store.set("token", S.token); store.set("code", code);
  return data;
}

// ------------------------------------------------------------------ consent
async function consentState(choice) {
  S.consent = await api("/api/consent", choice ? { choice } : {});
  return S.consent;
}

let consentAsking = null;
function ensureConsent() {
  if (consentAsking) return consentAsking;
  consentAsking = (async () => {
    const v = S.consent || await consentState();
    const ask = v.state === "pending" || (v.state === "none" && !store.get("consentSeen"));
    if (!ask) return;
    await Consent.ask({ view: v, send: consentState });
    store.set("consentSeen", "1");
    toast("Ďakujeme. Môžeš začať.");          // the same reply to either choice
  })().finally(() => { consentAsking = null; });
  return consentAsking;
}

$("consent-btn").addEventListener("click", async () => {
  try { await consentState(); } catch (_) { /* show what we have */ }
  if (S.consent) Consent.manage({ view: S.consent, send: consentState });
});

async function startApp() {
  S.config = await (await fetch("/api/config")).json();
  $("topic").textContent = S.config.topic;
  $("subject").textContent = ({ informatika: "Informatika", matematika: "Matematika", fyzika: "Fyzika" })[S.config.subject] || S.config.subject || "";
  document.title = `${S.config.topic} — hodina`;
  const hasAssistant = S.config.assistantEnabled;
  $("panel-assistant").hidden = !hasAssistant;
  $("workspace").classList.toggle("solo", !hasAssistant);
  $("tabbar").classList.toggle("enabled", hasAssistant);
  $("workspace").classList.toggle("tabbed", hasAssistant);
  $("login").hidden = true;
  $("app").hidden = false;
  await ensureConsent();                       // before the first task is shown
  await loadNext();
  startLoops();
}

$("start").addEventListener("click", async () => {
  const code = $("code").value.trim();
  $("login-error").textContent = "";
  if (!code) { $("login-error").textContent = "Zadaj kód z obálky."; return; }
  $("start").disabled = true;
  try {
    await login(code);
    await startApp();
  } catch (e) {
    $("login-error").textContent = e.message;
    $("code").select();
  } finally {
    $("start").disabled = false;
  }
});
$("code").addEventListener("keydown", (e) => { if (e.key === "Enter") $("start").click(); });

function logoutLocal() {
  store.del("token"); store.del("code"); store.del("consentSeen");
  S.token = null; S.code = null; S.consent = null;
}
let logoutArmed = false;
$("logout").addEventListener("click", async () => {
  if (!logoutArmed) {
    logoutArmed = true; $("logout").textContent = "Naozaj odhlásiť?";
    setTimeout(() => { logoutArmed = false; $("logout").textContent = "Odhlásiť"; }, 3000);
    return;
  }
  await flushTelemetry();
  try { await api("/api/logout", {}, { noRelogin: true }); } catch (_) {}
  logoutLocal();
  location.reload();
});

// ---------------------------------------------------------------- tasks
function setProgress(done, total) {
  const pct = total ? Math.round(100 * done / total) : 0;
  $("progress-bar").style.width = pct + "%";
  $("progress").setAttribute("aria-valuenow", String(done));
  $("progress").setAttribute("aria-valuemax", String(total));
  $("progress-text").textContent = `${done} / ${total} úloh`;
}

async function loadNext() {
  await flushTelemetry();
  const t = await api("/api/next", {});
  hideSelfcheck();
  $("feedback").textContent = ""; $("feedback").className = "feedback";
  $("gate-explain").hidden = true; $("solution-box").hidden = true;
  $("explanation").value = ""; $("explain-feedback").textContent = "";
  if (t.done) {
    S.task = null;
    setProgress(t.completed, t.total);
    $("task-area").hidden = true; $("done").hidden = false;
    $("done-text").textContent = t.skipped
      ? `Prešiel/prešla si všetky úlohy (${t.skipped} preskočených). Zavri notebook a počkaj na pokyn učiteľa.`
      : "Prešiel/prešla si všetky úlohy. Zavri notebook a počkaj na pokyn učiteľa.";
    ["prompt", "send"].forEach((id) => { const el = $(id); if (el) el.disabled = true; });
    return;
  }
  S.task = t;
  S.typed = false;
  S.pastedFromAssistant = false;
  $("task-area").hidden = false; $("done").hidden = true;
  setProgress(t.completed, t.total);
  $("task-title").textContent = `Úloha ${t.index} z ${t.total}`;
  $("task-kind").hidden = !t.kind;
  $("task-kind").textContent = t.kind === "scaffold" ? "Medzikrok" : t.kind === "harder" ? "Náročnejšia varianta" : "";
  $("task-skill").textContent = t.skillLabel || "";
  $("task-prompt").textContent = t.prompt;
  $("answer").value = "";
  $("answer").classList.toggle("code", /naprogramuj|program|pseudok/i.test(t.prompt));
  $("chat").innerHTML = "";
  $("chat").appendChild(h("p", { class: "chat-empty", id: "chat-empty", text: "Sem môžeš napísať otázku k úlohe, na ktorej práve pracuješ." }));
  ["submit", "solution", "skip", "answer", "prompt", "send"].forEach((id) => { const el = $(id); if (el) el.disabled = false; });
  showTab("panel-task");
  $("answer").focus({ preventScroll: true });
}

// the first keystroke is a measurement, not a UI event
$("answer").addEventListener("input", () => {
  if (S.typed || !S.task) return;
  S.typed = true;
  api("/api/event", { kind: "first_keystroke", taskId: S.task.taskId }).catch(() => {});
});

// ------------------------------------------------------- self-assessment
// Self-assessment is deliberate: automatic marking of free-text answers would
// be unreliable, and the graded outcome comes from the test, not from here.
// What this feeds is the knowledge-tracing estimate, for which a pupil's own
// judgement is adequate and cheap -- and, with the confidence, a measure of
// how well the pupil estimates their own correctness.
$("submit").addEventListener("click", () => {
  if (!S.task) return;
  if (!$("answer").value.trim()) { $("feedback").textContent = "Najprv napíš odpoveď."; $("feedback").className = "feedback warn"; return; }
  showSelfcheck();
});

function showSelfcheck() {
  S.self.choice = null;
  document.querySelectorAll("#self-choice button").forEach((b) => b.setAttribute("aria-pressed", "false"));
  const c = $("conf"); c.value = "50"; c.classList.add("unset"); c.dataset.touched = "";
  $("conf-val").textContent = "—";
  $("selfcheck-ok").disabled = true;
  $("selfcheck").hidden = false;
  $("submit").disabled = true;
  $("selfcheck").scrollIntoView({ behavior: "smooth", block: "nearest" });
}
function hideSelfcheck() { $("selfcheck").hidden = true; $("submit").disabled = false; }
function selfReady() { $("selfcheck-ok").disabled = !(S.self.choice !== null && $("conf").dataset.touched); }

document.querySelectorAll("#self-choice button").forEach((b) => b.addEventListener("click", () => {
  S.self.choice = b.dataset.v === "1";
  document.querySelectorAll("#self-choice button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
  selfReady();
}));
["input", "change"].forEach((evName) => $("conf").addEventListener(evName, () => {
  const c = $("conf"); c.dataset.touched = "1"; c.classList.remove("unset");
  $("conf-val").textContent = c.value + " %";
  selfReady();
}));
$("selfcheck-cancel").addEventListener("click", hideSelfcheck);

$("selfcheck-ok").addEventListener("click", async () => {
  if (!S.task) return;
  $("selfcheck-ok").disabled = true;
  try {
    const r = await api("/api/attempt", {
      taskId: S.task.taskId, answer: $("answer").value.trim(), correct: S.self.choice,
      confidence: parseInt($("conf").value, 10), pastedFromAssistant: S.pastedFromAssistant,
    });
    hideSelfcheck();
    if (r.correct) {
      $("feedback").textContent = "Zaznamenané. Pokračuješ ďalšou úlohou…";
      $("feedback").className = "feedback good";
      setTimeout(() => loadNext().catch((e) => toast(e.message, true)), 900);
    } else {
      $("feedback").textContent = S.config.assistantEnabled
        ? "Zaznamenané. Skús to ešte raz, alebo sa spýtaj asistenta."
        : "Zaznamenané. Skús to ešte raz.";
      $("feedback").className = "feedback warn";
    }
  } catch (e) {
    toast(e.message, true);
    $("selfcheck-ok").disabled = false;
  }
});

let skipArmed = false;
$("skip").addEventListener("click", async () => {
  if (!S.task) return;
  if (!skipArmed) {
    skipArmed = true; $("skip").textContent = "Naozaj preskočiť?";
    setTimeout(() => { skipArmed = false; $("skip").textContent = "Preskočiť úlohu"; }, 3000);
    return;
  }
  skipArmed = false; $("skip").textContent = "Preskočiť úlohu";
  try { await api("/api/skip", { taskId: S.task.taskId }); await loadNext(); }
  catch (e) { toast(e.message, true); }
});

// ------------------------------------------------- self-explanation gate
$("solution").addEventListener("click", async () => {
  if (!S.task) return;
  try {
    const r = await api("/api/solution", { taskId: S.task.taskId });
    if (r.mode === "later") {
      $("feedback").textContent = "Riešenie preberieme spoločne na konci hodiny.";
      $("feedback").className = "feedback";
    } else if (r.mode === "unlocked") {
      showSolution(r.solution);
    } else {
      $("gate-explain").hidden = false;
      $("explanation").focus();
    }
  } catch (e) { toast(e.message, true); }
});

function showSolution(text) {
  $("gate-explain").hidden = true;
  $("solution-text").textContent = text;
  $("solution-box").hidden = false;
  $("solution-box").scrollIntoView({ behavior: "smooth", block: "nearest" });
}

$("send-explanation").addEventListener("click", async () => {
  const text = $("explanation").value.trim();
  $("send-explanation").disabled = true;
  try {
    const r = await api("/api/explain", { taskId: S.task.taskId, text });
    $("explain-feedback").textContent = r.reason;
    $("explain-feedback").className = "feedback " + (r.accepted ? "good" : "warn");
    if (r.accepted && r.solution) showSolution(r.solution);
  } catch (e) { toast(e.message, true); }
  finally { $("send-explanation").disabled = false; }
});

// ------------------------------------------------------------ assistant
function bubble(role, text) {
  const empty = $("chat-empty");
  if (empty) empty.remove();
  const d = h("div", { class: "msg " + role, text });
  $("chat").appendChild(d);
  $("chat").scrollTop = $("chat").scrollHeight;
  return d;
}

$("send").addEventListener("click", async () => {
  const text = $("prompt").value.trim();
  if (!text || !S.task || S.asking) return;
  S.asking = true;
  $("send").disabled = true;
  bubble("user", text);
  $("prompt").value = "";
  autosize($("prompt"));
  const pending = bubble("assistant", "");
  pending.appendChild(h("span", { class: "typing", "aria-label": "Asistent píše" }, h("i"), h("i"), h("i")));
  try {
    const r = await api("/api/ask", { taskId: S.task.taskId, prompt: text, draft: $("answer").value });
    pending.textContent = r.text;
    if (r.degraded) pending.classList.add("warn");
  } catch (e) {
    pending.textContent = e.status === 429 ? "Počkaj chvíľu a skús to znova." : "Asistent nie je dostupný (" + e.message + ").";
    pending.classList.add("warn");
  } finally {
    S.asking = false;
    $("send").disabled = false;
    $("chat").scrollTop = $("chat").scrollHeight;
  }
});
$("prompt").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("send").click(); }
});
function autosize(el) { el.style.height = "auto"; el.style.height = Math.min(el.scrollHeight, 160) + "px"; }
$("prompt").addEventListener("input", () => autosize($("prompt")));

// ---------------------------------------------------- copy / paste signals
const norm = (s) => (s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/\s+/g, " ").trim();
function assistantText() {
  return Array.from(document.querySelectorAll("#chat .msg.assistant")).map((m) => norm(m.textContent)).join(" \n ");
}
function sourceOf(node) {
  const el = node && (node.nodeType === 1 ? node : node.parentElement);
  if (!el) return "other";
  if (el.closest("#chat")) return el.closest(".msg.assistant") ? "assistant" : "other";
  if (el.closest("#task-prompt")) return "task";
  if (el.closest("#answer")) return "answer";
  if (el.closest("#activity-body")) return "activity";
  return "other";
}
document.addEventListener("copy", () => {
  const sel = document.getSelection();
  const text = sel ? String(sel) : "";
  if (!text.trim() || !S.task) return;
  api("/api/event", { kind: "copy", taskId: S.task.taskId, source: sourceOf(sel.anchorNode), chars: text.length }).catch(() => {});
});
function watchPaste(id, target) {
  $(id).addEventListener("paste", (e) => {
    const text = (e.clipboardData || window.clipboardData).getData("text") || "";
    if (!text || !S.task) return;
    const n = norm(text);
    const fromAssistant = n.length >= 8 && assistantText().includes(n.slice(0, 200));
    if (fromAssistant && target === "answer") S.pastedFromAssistant = true;
    api("/api/event", { kind: "paste", taskId: S.task.taskId, target, chars: text.length, fromAssistant }).catch(() => {});
  });
}
watchPaste("answer", "answer");
watchPaste("prompt", "prompt");
watchPaste("explanation", "explanation");

// ---------------------------------------------------------- telemetry
const T = { clicks: 0, keys: 0, focusLoss: 0, hiddenMs: 0, activeMs: 0, idleMs: 0, lastInput: Date.now(), last: Date.now() };
const IDLE_AFTER_MS = 30000;
document.addEventListener("pointerdown", () => { T.clicks++; T.lastInput = Date.now(); }, true);
document.addEventListener("keydown", () => { T.keys++; T.lastInput = Date.now(); }, true);
document.addEventListener("scroll", () => { T.lastInput = Date.now(); }, true);
document.addEventListener("visibilitychange", () => { tick(); if (document.hidden) { T.focusLoss++; flushTelemetry(true); } });
window.addEventListener("blur", () => { if (!document.hidden) T.focusLoss++; });
window.addEventListener("pagehide", () => flushTelemetry(true));

function tick() {
  const now = Date.now();
  const dt = Math.min(now - T.last, 60000);
  T.last = now;
  if (document.hidden) T.hiddenMs += dt;
  else if (now - T.lastInput < IDLE_AFTER_MS) T.activeMs += dt;
  else T.idleMs += dt;
  if (S.activity.open && !document.hidden) S.activity.msVisible += dt;
}
async function flushTelemetry(keepalive) {
  tick();
  if (!S.token) return;
  const payload = { taskId: S.task ? S.task.taskId : null, view: currentView(),
                    clicks: T.clicks, keys: T.keys, focusLoss: T.focusLoss,
                    hiddenMs: T.hiddenMs, activeMs: T.activeMs, idleMs: T.idleMs };
  if (!payload.clicks && !payload.keys && !payload.hiddenMs && !payload.activeMs && !payload.idleMs) return;
  T.clicks = T.keys = T.focusLoss = 0; T.hiddenMs = T.activeMs = T.idleMs = 0;
  try { await api("/api/telemetry", payload, { keepalive: !!keepalive, noRelogin: !!keepalive }); } catch (_) {}
}
function currentView() {
  if (S.activity.open) return "activity";
  const a = document.querySelector(".workspace .panel.active");
  return a && a.id === "panel-assistant" ? "assistant" : "task";
}

// ------------------------------------------------------- live activity
async function pulse() {
  let p;
  try { p = await api("/api/pulse"); } catch (_) { return; }
  const cur = p.activity;
  const A = S.activity;
  if (!cur) { if (A.id) closeActivity(); return; }
  if (cur.id !== A.id || cur.version !== A.version || cur.revealed !== A.revealed) {
    const fresh = cur.id !== A.id || cur.version !== A.version;
    const view = await api("/api/activity");
    if (!view.activity) return;
    if (fresh) { await sendEngagement(); A.msVisible = 0; }
    A.id = cur.id; A.version = cur.version; A.revealed = cur.revealed; A.view = view;
    renderActivity(view);
    if (fresh || cur.revealed) openActivity();
  }
}

function renderActivity(view) {
  const A = S.activity;
  if (A.handle && A.handle.destroy) A.handle.destroy();
  $("activity-title").textContent = view.activity.title;
  $("activity-type").textContent = window.Activity.TYPE_LABELS[view.activity.type] || "Aktivita";
  A.handle = window.Activity.render($("activity-body"), view, {
    submit: (response) => api("/api/activity/respond", { activityId: view.activity.id, version: view.version, response })
      .then((r) => { A.view.mine = r.mine; return r; }),
  });
}
function openActivity() {
  S.activity.open = true;
  $("activity-layer").hidden = false;
  $("activity-pill").hidden = true;
  tick();
}
function hideActivity() {
  tick();
  S.activity.open = false;
  $("activity-layer").hidden = true;
  $("activity-pill").hidden = !S.activity.id;
}
async function closeActivity() {
  await sendEngagement();
  const A = S.activity;
  if (A.handle && A.handle.destroy) A.handle.destroy();
  Object.assign(A, { id: null, version: null, revealed: null, view: null, handle: null, open: false, msVisible: 0 });
  $("activity-layer").hidden = true;
  $("activity-pill").hidden = true;
  $("activity-body").innerHTML = "";
}
async function sendEngagement() {
  const A = S.activity;
  if (!A.id) return;
  tick();
  const st = (A.handle && typeof A.handle.stats === "function" ? A.handle.stats() : null) || {};
  try {
    await api("/api/activity/engage", { activityId: A.id, version: A.version, steps: st.steps || 0, plays: st.plays || 0,
      predictions: st.predictions || 0, predictionsCorrect: st.predictionsCorrect || 0, msVisible: Math.round(A.msVisible) });
  } catch (_) {}
}
$("activity-hide").addEventListener("click", hideActivity);
$("activity-pill").addEventListener("click", openActivity);

// ------------------------------------------------------------ mobile tabs
function showTab(id) {
  document.querySelectorAll("#tabbar button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === id ? "true" : "false"));
  document.querySelectorAll(".workspace > .panel").forEach((p) => p.classList.toggle("active", p.id === id));
}
document.querySelectorAll("#tabbar button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));

// ---------------------------------------------------------------- loops
let loopsStarted = false;
function startLoops() {
  if (loopsStarted) return;
  loopsStarted = true;
  setInterval(tick, 1000);
  setInterval(() => flushTelemetry(false), 30000);
  pulse();
  setInterval(pulse, 3000);
}

// ---------------------------------------------------------------- boot
(async function boot() {
  try {
    const cfg = await (await fetch("/api/config")).json();
    if (cfg.codeFormat) $("code").placeholder = "napr. " + cfg.codeFormat;
  } catch (_) {}
  if (S.token && S.code) {
    try { await startApp(); return; } catch (_) { logoutLocal(); }
  }
  $("login").hidden = false;
  $("code").focus();
})();

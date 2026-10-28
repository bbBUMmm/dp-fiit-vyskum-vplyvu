/* app.js -- the pupil-facing client.
 *
 * Two things here matter for the research rather than for the user:
 *
 *   1. The first keystroke on a task is reported to the server. Without it,
 *      "time to first prompt" cannot distinguish a pupil who read the task for
 *      ninety seconds from one who never looked at it.
 *   2. The assistant panel is hidden in condition K, but that is cosmetic --
 *      the server refuses the endpoint as well, and a request from a pupil who
 *      found it anyway is logged as a protocol deviation.
 */
"use strict";

const $ = (id) => document.getElementById(id);
const state = { student: null, task: null, config: null, typed: false };

async function api(path, body) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ student: state.student, ...body }),
  });
  if (!r.ok) {
    let detail = r.statusText;
    try { detail = (await r.json()).error || detail; } catch (_) {}
    throw new Error(detail);
  }
  return r.json();
}

/* ---------------------------------------------------------------- start */
$("start").addEventListener("click", async () => {
  const code = $("code").value.trim();
  if (!code) { $("banner").textContent = "Zadaj kód."; return; }
  state.student = code;

  state.config = await (await fetch("/api/config")).json();
  $("topic").textContent = state.config.topic;
  if (state.config.assistantEnabled) $("assistant").hidden = false;
  $("unlock").hidden = !state.config.adaptive && false;

  $("gate").hidden = true;
  $("app").hidden = false;
  await loadNext();
});

$("code").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("start").click();
});

/* ----------------------------------------------------------------- task */
async function loadNext() {
  const t = await api("/api/next", {});
  if (t.done) {
    $("task-prompt").textContent =
      "Hotovo. Zavri notebook a počkaj na pokyn učiteľa.";
    $("task-id").textContent = "—";
    ["answer", "submit", "unlock", "prompt", "send"].forEach(
      (id) => { const el = $(id); if (el) el.disabled = true; });
    return;
  }
  state.task = t;
  state.typed = false;
  $("task-id").textContent = t.taskId;
  $("task-prompt").textContent = t.prompt;
  $("answer").value = "";
  $("feedback").textContent = "";
  $("chat").innerHTML = "";
  $("gate-explain").hidden = true;
  $("explanation").value = "";
  $("explain-feedback").textContent = "";
}

/* the first keystroke is a measurement, not a UI event */
$("answer").addEventListener("input", () => {
  if (state.typed || !state.task) return;
  state.typed = true;
  api("/api/event", { kind: "first_keystroke", taskId: state.task.taskId })
    .catch(() => {});
});

$("submit").addEventListener("click", async () => {
  if (!state.task) return;
  const answer = $("answer").value.trim();
  if (!answer) { $("feedback").textContent = "Napíš odpoveď."; return; }

  // Self-assessment is deliberate: automatic marking of free-text answers
  // would be unreliable, and the graded outcome comes from the paper test, not
  // from here. What this feeds is the knowledge-tracing estimate, for which a
  // pupil's own judgement is adequate and cheap.
  const correct = confirm(
    "Porovnaj svoju odpoveď so zadaním.\n\n" +
    "Stlač OK, ak si si istý, že je správna.\n" +
    "Stlač Zrušiť, ak si nie si istý alebo je nesprávna.");

  const r = await api("/api/attempt", {
    taskId: state.task.taskId, answer, correct,
  });
  $("feedback").textContent = r.correct
    ? "Zaznamenané. Pokračuj ďalšou úlohou."
    : "Zaznamenané. Skús to ešte raz alebo sa spýtaj asistenta.";
  if (r.correct) setTimeout(loadNext, 900);
});

/* ------------------------------------------------- self-explanation gate */
$("unlock").addEventListener("click", async () => {
  if (!state.task) return;
  if (!state.config.adaptive) {
    $("feedback").textContent = "Riešenie preberieme spoločne na konci hodiny.";
    return;
  }
  $("gate-explain").hidden = false;
  $("explanation").focus();
});

$("send-explanation").addEventListener("click", async () => {
  const text = $("explanation").value.trim();
  const r = await api("/api/explain", { taskId: state.task.taskId, text });
  $("explain-feedback").textContent = r.reason;
  $("explain-feedback").className = "feedback " + (r.accepted ? "good" : "warn");
  if (r.accepted) {
    $("gate-explain").hidden = true;
    $("feedback").textContent =
      "Riešenie preberieme spoločne na konci hodiny — ale tvoje vysvetlenie " +
      "je to, na čom záleží.";
  }
});

/* ------------------------------------------------------------ assistant */
function bubble(role, text) {
  const d = document.createElement("div");
  d.className = "msg " + role;
  d.textContent = text;
  $("chat").appendChild(d);
  $("chat").scrollTop = $("chat").scrollHeight;
  return d;
}

$("send").addEventListener("click", async () => {
  const text = $("prompt").value.trim();
  if (!text || !state.task) return;
  bubble("user", text);
  $("prompt").value = "";
  const pending = bubble("assistant", "…");
  try {
    const r = await api("/api/ask", {
      taskId: state.task.taskId,
      prompt: text,
      hintLevel: state.task.hintLevel,
    });
    pending.textContent = r.text;
    if (r.degraded) pending.classList.add("warn");
  } catch (e) {
    pending.textContent = "Asistent nie je dostupný (" + e.message + ").";
    pending.classList.add("warn");
  }
});

$("prompt").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("send").click(); }
});

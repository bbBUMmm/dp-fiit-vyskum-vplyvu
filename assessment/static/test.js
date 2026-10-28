// test.js -- the pupil-facing test client.
//
// Three things here are measurements and not interface:
//
//   * blur_seconds. The time the test window spent not focused while an item was
//     open. It is the only trace a tab switch leaves, and tab switching is the
//     cheapest way to look an answer up.
//   * paste_events. A pasted free-text answer was not written.
//   * revisions. How many times the pupil changed an answer before submitting,
//     which separates a considered change of mind from a first guess.
//
// All three are recorded, none is shown to the pupil, and none is ever treated
// as proof on its own -- integrity.py needs two independent families.
//
// The client gives NO feedback about correctness. This test sits between two
// measurements of learning; telling a pupil the answer would make it a third.

let token = null, current = null, totalItems = 0;
let blurStart = null, blurAccum = 0, pastes = 0, revisions = 0;

const el = (id) => document.getElementById(id);

window.addEventListener("blur", () => { blurStart = Date.now(); });
window.addEventListener("focus", () => {
  if (blurStart) { blurAccum += (Date.now() - blurStart) / 1000; blurStart = null; }
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) { blurStart = blurStart || Date.now(); }
  else if (blurStart) { blurAccum += (Date.now() - blurStart) / 1000; blurStart = null; }
});

async function post(path, body, hdr) {
  const h = Object.assign({ "Content-Type": "application/json" }, hdr || {});
  const r = await fetch(path, { method: "POST", headers: h,
                               body: JSON.stringify(body || {}) });
  return { ok: r.ok, data: await r.json() };
}

async function boot() {
  const info = await (await fetch("/api/info")).json();
  el("title").textContent = info.title;
  el("sub").textContent = `${info.items} položiek · stretnutie ${info.session}`;
  totalItems = info.items;
  askForCode();
}

function askForCode() {
  el("card").innerHTML = `
    <p class="stem">Zadaj kód z obálky.</p>
    <input type="text" id="code" autocomplete="off" autocapitalize="characters"
           spellcheck="false" placeholder="GY-XXXXX-X">
    <div class="err" id="cerr"></div>
    <button id="go">Začať</button>
    <p class="note">Kód nie je tvoje meno. Výsledok nemá vplyv na známku a
       kedykoľvek môžeš prestať bez následku.</p>`;
  el("go").onclick = start;
  el("code").addEventListener("keydown", (e) => { if (e.key === "Enter") start(); });
  el("code").focus();
}

async function start() {
  const code = el("code").value;
  el("go").disabled = true;
  const { ok, data } = await post("/api/start", { code });
  if (!ok) {
    el("cerr").textContent = data.error;
    el("go").disabled = false;
    el("code").select();
    return;
  }
  token = data.token;
  nextItem();
}

async function nextItem() {
  blurAccum = 0; pastes = 0; revisions = 0; blurStart = null;
  const { data } = await post("/api/item", {}, { "X-Sitting": token });
  if (data.done) return finish(data);
  current = data.item;
  render(data);
}

function render(d) {
  const it = d.item;
  el("bar").style.width = `${((d.index - 1) / d.total) * 100}%`;
  let input = "";
  if (it.format === "mc4" || it.format === "mc3" || it.format === "choice") {
    input = it.options.map((o, i) => `
      <label class="opt" data-i="${i}">
        <input type="radio" name="ans" value="${i}">${o}</label>`).join("");
  } else if (it.format === "open" || it.format === "table" || it.format === "text") {
    input = `<textarea id="free" placeholder="${it.rubric_hint}"></textarea>`;
  } else if (it.format === "numeric") {
    input = `<input type="text" id="free" inputmode="numeric" autocomplete="off">`;
  } else if (it.format === "likert5" || it.format === "likert7") {
    const n = it.format === "likert5" ? 5 : 7;
    input = Array.from({ length: n }, (_, i) => `
      <label class="opt" data-i="${i}">
        <input type="radio" name="ans" value="${i + 1}">${i + 1}</label>`).join("");
  } else if (it.format === "scale0_10") {
    input = `<input type="range" id="free" min="0" max="10" value="5"
                    style="width:100%">`;
  } else if (it.format === "multi") {
    input = it.options.map((o, i) => `
      <label class="opt" data-i="${i}">
        <input type="checkbox" name="ans" value="${i}">${o}</label>`).join("");
  }

  const jol = it.jol ? `
    <div class="jol">
      <label for="jolr">Nakoľko si si istý/á, že tvoja odpoveď je správna?
        <span class="jolval" id="jolv">50</span>&nbsp;%</label>
      <input type="range" id="jolr" min="0" max="100" value="50">
    </div>` : "";

  el("card").innerHTML = `
    <div class="sub">Položka ${d.index} z ${d.total}</div>
    <p class="stem">${escapeHtml(it.stem)}</p>
    ${input}${jol}
    <div class="err" id="aerr"></div>
    <button id="next">Ďalej</button>`;

  if (it.jol) {
    const r = el("jolr");
    r.addEventListener("input", () => { el("jolv").textContent = r.value; });
  }
  document.querySelectorAll('input[name="ans"]').forEach((inp) => {
    inp.addEventListener("change", (e) => {
      revisions++;
      document.querySelectorAll(".opt").forEach((l) => l.classList.remove("sel"));
      if (e.target.type === "radio") e.target.closest(".opt").classList.add("sel");
      else e.target.closest(".opt").classList.toggle("sel", e.target.checked);
    });
  });
  const free = el("free");
  if (free) {
    free.addEventListener("paste", () => { pastes++; });
    free.addEventListener("input", () => { revisions++; });
    free.focus();
  }
  el("next").onclick = submit;
}

async function submit() {
  let raw = null;
  const free = el("free");
  if (free) raw = free.value;
  else {
    const checked = [...document.querySelectorAll('input[name="ans"]:checked')]
      .map((x) => x.value);
    raw = checked.join(",");
  }
  if (raw === null || raw.trim() === "") {
    el("aerr").textContent =
      "Odpoveď je prázdna. Ak nevieš, napíš „neviem“ — aj to je odpoveď.";
    return;
  }
  el("next").disabled = true;
  if (blurStart) { blurAccum += (Date.now() - blurStart) / 1000; blurStart = null; }
  const jr = el("jolr");
  await post("/api/answer", {
    item_id: current.id, raw,
    jol: jr ? Number(jr.value) : null,
    paste_events: pastes, blur_seconds: blurAccum, revisions
  }, { "X-Sitting": token });
  nextItem();
}

function finish(d) {
  el("bar").style.width = "100%";
  el("card").innerHTML = `
    <p class="stem">Hotovo. Odpovedal/a si na ${d.answered} položiek.</p>
    <p class="note">Výsledok sa nezobrazuje: tento test meria, čo si sa naučil/a,
      a ukázať správne odpovede by z neho urobilo ďalšiu hodinu. Celé zadania aj
      odpovede dostaneš po skončení štúdie.</p>
    <p class="note">Môžeš zavrieť okno.</p>`;
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

boot();

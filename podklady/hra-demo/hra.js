/* =====================================================================
   AI DETEKTÍV — HERNÝ ENGINE
   Stav, adaptivita, skórovanie, behaviorálne logovanie, export JSON.
   Plain script (bez ES modulov) → funguje aj po otvorení cez file://
   ===================================================================== */

const SESSION_LEN = 12;        // koľko uzlov za jedno sedenie
const MODE_LABELS = {
  adaptivny: "Adaptívna AI (prispôsobuje sa)",
  genericky: "Generická AI (statická)",
  kontrola:  "Bez asistencie (kontrola)",
};

const state = {
  mode: null,
  studentId: "",
  queue: [],            // poradie ID položiek pre toto sedenie
  pool: [],             // ešte nepoužité položky (pre adaptívny výber)
  idx: 0,
  responses: [],        // záznamy odpovedí
  diffTarget: 1,        // cieľová obtiažnosť (adaptívny režim)
  itemStart: 0,         // timestamp začiatku aktuálnej položky
  hintsThisItem: 0,
  answeredCurrent: false,
};

/* ---------- ŠTART ---------- */
function startGame() {
  const id = document.getElementById("studentId").value.trim() || "anonym";
  const mode = document.querySelector('input[name="mode"]:checked').value;
  state.mode = mode;
  state.studentId = id;
  state.responses = [];
  state.idx = 0;
  state.diffTarget = 1;
  state.pool = BANKA.slice();
  state.queue = buildInitialQueue(mode);
  show("screen-game");
  renderCurrent();
}

/* Generický/kontrola: vyvážené zamiešané poradie.
   Adaptívny: prvú položku vyberáme podľa cieľovej obtiažnosti, ďalšie dynamicky. */
function buildInitialQueue(mode) {
  if (mode === "adaptivny") {
    // začneme ľahkou položkou; ďalšie doberáme v nextItem()
    const first = pickByDifficulty(1);
    return first ? [first.id] : [];
  }
  // vyvážene: zamiešaj, ale snaž sa striedať dimenzie
  const shuffled = shuffle(BANKA.slice());
  return shuffled.slice(0, Math.min(SESSION_LEN, shuffled.length)).map(it => it.id);
}

function pickByDifficulty(target) {
  if (state.pool.length === 0) return null;
  // vyber nepoužitú položku s obtiažnosťou najbližšie k cieľu (náhodný tie-break)
  let best = null, bestDist = Infinity;
  for (const it of shuffle(state.pool)) {
    const d = Math.abs(it.difficulty - target);
    if (d < bestDist) { bestDist = d; best = it; }
  }
  if (best) state.pool = state.pool.filter(x => x.id !== best.id);
  return best;
}

/* ---------- RENDER POLOŽKY ---------- */
function getItem(id) { return BANKA.find(x => x.id === id); }

function renderCurrent() {
  state.answeredCurrent = false;
  state.hintsThisItem = 0;
  const item = getItem(state.queue[state.idx]);
  if (!item) { finish(); return; }

  const total = (state.mode === "adaptivny") ? SESSION_LEN : state.queue.length;
  document.getElementById("progress").textContent =
    `Uzol ${state.idx + 1} / ${total}`;
  document.getElementById("progressBar").style.width =
    `${((state.idx) / total) * 100}%`;
  document.getElementById("modeChip").textContent = MODE_LABELS[state.mode];

  document.getElementById("brief").textContent = item.brief;

  // AI vstup (v kontrolnom režime zobrazený ako "nájdené tvrdenie", bez nápovedy)
  const aiBox = document.getElementById("aiBox");
  if (item.aiSays) {
    aiBox.style.display = "block";
    document.getElementById("aiLabel").textContent =
      (state.mode === "kontrola") ? "🔎 Tvrdenie na posúdenie" : "🤖 AI asistent hovorí";
    document.getElementById("aiSays").textContent = item.aiSays;
  } else {
    aiBox.style.display = "none";
  }

  document.getElementById("question").textContent = item.question;

  // možnosti (zamiešané, aby poradie neprezrádzalo správnu)
  const optWrap = document.getElementById("options");
  optWrap.innerHTML = "";
  const order = shuffle(item.options.map((o, i) => i));
  order.forEach(origIdx => {
    const opt = item.options[origIdx];
    const btn = document.createElement("button");
    btn.className = "option";
    btn.textContent = opt.text;
    btn.onclick = () => selectOption(item, origIdx, btn);
    optWrap.appendChild(btn);
  });

  // tlačidlo nápovedy (len adaptívny/generický režim a ak je AI vstup)
  const hintBtn = document.getElementById("hintBtn");
  hintBtn.style.display = (state.mode !== "kontrola" && item.aiSays) ? "inline-block" : "none";
  document.getElementById("hintText").style.display = "none";

  document.getElementById("feedback").style.display = "none";
  document.getElementById("nextBtn").style.display = "none";

  state.itemStart = performance.now();
}

/* ---------- NÁPOVEDA (zachytáva sa ako behaviorálny ukazovateľ) ---------- */
function askHint() {
  const item = getItem(state.queue[state.idx]);
  state.hintsThisItem++;
  let hint;
  if (state.mode === "adaptivny") {
    // sokratická, prispôsobená výkonu
    const doingWell = recentMeanScore() >= 1.4;
    hint = doingWell
      ? "Polož si otázku: čím konkrétne by si toto tvrdenie overil nezávisle od AI?"
      : "Tip: AI znie sebavedomo aj keď sa mýli. Daj sa správnosť overiť, nepreberaj automaticky.";
  } else {
    hint = "Tip: zváž, či sa odpoveď dá nezávisle overiť a či zdroj/argument obstojí.";
  }
  const ht = document.getElementById("hintText");
  ht.textContent = "💡 " + hint;
  ht.style.display = "block";
}

/* ---------- VÝBER MOŽNOSTI ---------- */
function selectOption(item, origIdx, btn) {
  if (state.answeredCurrent) return;
  state.answeredCurrent = true;
  const timeMs = Math.round(performance.now() - state.itemStart);
  const opt = item.options[origIdx];

  // záznam
  state.responses.push({
    id: item.id, type: item.type, dimension: item.dimension,
    difficulty: item.difficulty, aiCorrect: item.aiCorrect,
    chosenText: opt.text, score: opt.score,
    reliance: !!opt.reliance, correct: !!opt.correct,
    timeMs, hintsUsed: state.hintsThisItem,
  });

  // vizuálne označenie
  Array.from(document.getElementById("options").children).forEach(b => {
    b.classList.add("disabled");
    if (b === btn) b.classList.add(opt.score === 2 ? "good" : opt.score === 0 ? "bad" : "mid");
  });

  // spätná väzba
  const fb = document.getElementById("feedback");
  fb.className = "feedback " + (opt.score === 2 ? "good" : opt.score === 0 ? "bad" : "mid");
  fb.innerHTML = `<strong>${opt.score === 2 ? "✅ Výborne" : opt.score === 0 ? "✗ Chyba" : "◐ Čiastočne"} (${opt.score}/2)</strong><br>${opt.feedback}`;
  fb.style.display = "block";

  // adaptivita: uprav cieľovú obtiažnosť
  if (state.mode === "adaptivny") {
    if (opt.score === 2) state.diffTarget = Math.min(3, state.diffTarget + 1);
    else if (opt.score === 0) state.diffTarget = Math.max(1, state.diffTarget - 1);
  }

  document.getElementById("progressBar").style.width =
    `${((state.idx + 1) / ((state.mode === "adaptivny") ? SESSION_LEN : state.queue.length)) * 100}%`;

  const nextBtn = document.getElementById("nextBtn");
  const total = (state.mode === "adaptivny") ? SESSION_LEN : state.queue.length;
  nextBtn.textContent = (state.idx + 1 >= total) ? "Zobraziť výsledky →" : "Ďalší uzol →";
  nextBtn.style.display = "inline-block";
  document.getElementById("hintBtn").style.display = "none";
  document.getElementById("hintText").style.display = "none";
}

function nextItem() {
  const total = (state.mode === "adaptivny") ? SESSION_LEN : state.queue.length;
  if (state.idx + 1 >= total) { finish(); return; }
  state.idx++;
  if (state.mode === "adaptivny") {
    // doberieme ďalšiu položku podľa aktuálnej cieľovej obtiažnosti
    const next = pickByDifficulty(state.diffTarget);
    if (next) state.queue.push(next.id);
    else { finish(); return; } // minuli sa položky
  }
  renderCurrent();
}

/* ---------- VÝSLEDKY ---------- */
function recentMeanScore() {
  const last = state.responses.slice(-3);
  if (last.length === 0) return 1;
  return last.reduce((s, r) => s + r.score, 0) / last.length;
}

function computeResults() {
  const dims = {};
  for (const key of Object.keys(DIMENZIE)) dims[key] = { sum: 0, max: 0, n: 0 };
  state.responses.forEach(r => {
    dims[r.dimension].sum += r.score;
    dims[r.dimension].max += 2;
    dims[r.dimension].n += 1;
  });
  const dimPct = {};
  for (const key of Object.keys(dims)) {
    dimPct[key] = dims[key].max > 0 ? Math.round((dims[key].sum / dims[key].max) * 100) : null;
  }

  const totalScore = state.responses.reduce((s, r) => s + r.score, 0);
  const totalMax = state.responses.length * 2;
  const overallPct = totalMax > 0 ? Math.round((totalScore / totalMax) * 100) : 0;

  // offloading index: % uzlov, kde žiak slepo prebral AI (reliance) –
  //   obzvlášť závažné, keď bola AI nesprávna
  const relianceAll = state.responses.filter(r => r.reliance).length;
  const relianceOnWrong = state.responses.filter(r => r.reliance && r.aiCorrect === false).length;
  const offloadingIdx = state.responses.length
    ? Math.round((relianceAll / state.responses.length) * 100) : 0;

  const times = state.responses.map(r => r.timeMs).sort((a, b) => a - b);
  const medianTime = times.length ? times[Math.floor(times.length / 2)] : 0;
  const hintsTotal = state.responses.reduce((s, r) => s + r.hintsUsed, 0);

  return {
    studentId: state.studentId, mode: state.mode,
    timestamp: new Date().toISOString(),
    nItems: state.responses.length,
    overallPct, dimPct,
    offloadingIdx, relianceOnWrong,
    behaviour: { medianTimeMs: medianTime, hintsTotal },
    responses: state.responses,
  };
}

function finish() {
  const res = computeResults();
  state._lastResults = res;
  // záloha do localStorage
  try {
    const key = "aidetektiv_" + state.studentId + "_" + Date.now();
    localStorage.setItem(key, JSON.stringify(res));
  } catch (e) {}

  show("screen-results");
  document.getElementById("resMode").textContent = MODE_LABELS[res.mode];
  document.getElementById("resId").textContent = res.studentId;
  document.getElementById("resOverall").textContent = res.overallPct + " %";
  document.getElementById("resOffload").textContent = res.offloadingIdx + " %";
  document.getElementById("resOffloadWrong").textContent = res.relianceOnWrong + "×";
  document.getElementById("resTime").textContent = (res.behaviour.medianTimeMs / 1000).toFixed(1) + " s";

  // radar + bary
  drawRadar(document.getElementById("radar"), res.dimPct);
  const bars = document.getElementById("bars");
  bars.innerHTML = "";
  for (const key of Object.keys(DIMENZIE)) {
    if (res.dimPct[key] === null) continue;
    const row = document.createElement("div");
    row.className = "barRow";
    row.innerHTML = `
      <div class="barLabel">${DIMENZIE[key].nazov}</div>
      <div class="barTrack"><div class="barFill" style="width:${res.dimPct[key]}%;background:${DIMENZIE[key].farba}"></div></div>
      <div class="barVal">${res.dimPct[key]} %</div>`;
    bars.appendChild(row);
  }

  document.getElementById("jsonOut").value = JSON.stringify(res, null, 2);
}

/* ---------- RADAROVÝ GRAF (čistý canvas, bez knižníc) ---------- */
function drawRadar(canvas, dimPct) {
  const keys = Object.keys(DIMENZIE).filter(k => dimPct[k] !== null);
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const cx = W / 2, cy = H / 2 + 6, R = Math.min(W, H) / 2 - 54;
  ctx.clearRect(0, 0, W, H);
  const N = keys.length;
  if (N < 3) return;

  // mriežka
  ctx.strokeStyle = "rgba(148,163,184,0.25)";
  ctx.fillStyle = "rgba(148,163,184,0.6)";
  ctx.lineWidth = 1;
  for (let ring = 1; ring <= 4; ring++) {
    const rr = (R * ring) / 4;
    ctx.beginPath();
    for (let i = 0; i <= N; i++) {
      const a = (Math.PI * 2 * i) / N - Math.PI / 2;
      const x = cx + rr * Math.cos(a), y = cy + rr * Math.sin(a);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  // osi + popisy
  ctx.font = "12px system-ui, sans-serif";
  keys.forEach((k, i) => {
    const a = (Math.PI * 2 * i) / N - Math.PI / 2;
    const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
    ctx.strokeStyle = "rgba(148,163,184,0.25)";
    ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(x, y); ctx.stroke();
    const lx = cx + (R + 26) * Math.cos(a), ly = cy + (R + 18) * Math.sin(a);
    ctx.fillStyle = "#cbd5e1";
    ctx.textAlign = Math.abs(Math.cos(a)) < 0.3 ? "center" : (Math.cos(a) > 0 ? "left" : "right");
    const short = DIMENZIE[k].nazov.split(" ")[0];
    ctx.fillText(short, lx, ly);
  });
  // dáta
  ctx.beginPath();
  keys.forEach((k, i) => {
    const v = dimPct[k] / 100;
    const a = (Math.PI * 2 * i) / N - Math.PI / 2;
    const x = cx + R * v * Math.cos(a), y = cy + R * v * Math.sin(a);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fillStyle = "rgba(96,165,250,0.25)";
  ctx.strokeStyle = "#60a5fa";
  ctx.lineWidth = 2;
  ctx.fill(); ctx.stroke();
  keys.forEach((k, i) => {
    const v = dimPct[k] / 100;
    const a = (Math.PI * 2 * i) / N - Math.PI / 2;
    const x = cx + R * v * Math.cos(a), y = cy + R * v * Math.sin(a);
    ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fillStyle = "#60a5fa"; ctx.fill();
  });
}

/* ---------- EXPORT ---------- */
function downloadJSON() {
  const res = state._lastResults || computeResults();
  const blob = new Blob([JSON.stringify(res, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `aidetektiv_${res.studentId}_${res.mode}.json`;
  a.click();
}
function copyJSON() {
  const ta = document.getElementById("jsonOut");
  ta.select(); document.execCommand("copy");
  const btn = document.getElementById("copyBtn");
  const t = btn.textContent; btn.textContent = "Skopírované ✓";
  setTimeout(() => btn.textContent = t, 1500);
}
function restart() { show("screen-start"); }

/* ---------- POMOCNÉ ---------- */
function shuffle(arr) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}
function show(id) {
  document.querySelectorAll(".screen").forEach(s => s.style.display = "none");
  document.getElementById(id).style.display = "block";
}

window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("startBtn").onclick = startGame;
  document.getElementById("hintBtn").onclick = askHint;
  document.getElementById("nextBtn").onclick = nextItem;
  document.getElementById("downloadBtn").onclick = downloadJSON;
  document.getElementById("copyBtn").onclick = copyJSON;
  document.getElementById("restartBtn").onclick = restart;
});

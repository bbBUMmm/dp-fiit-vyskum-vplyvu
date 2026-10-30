/* widgets.js -- the interactive part of the lesson, as the pupil sees it.
 *
 * Two layers:
 *   Widgets   self-contained simulations and animations (binary search step by
 *             step, linear vs binary race, guess-the-number, compound interest,
 *             series/parallel circuit, generic frame animation);
 *   Activity  the six activity types (poll, predict, order, animation,
 *             handson, reflect) built from those widgets and plain inputs.
 *
 * Shared by the pupil app and the teacher's preview, so what the teacher
 * previews is exactly what thirty screens will show.
 *
 * Nothing here reads the experimental condition. Every piece of text that comes
 * from an activity definition is inserted as text, never as HTML; the one
 * exception, inline SVG in a frame animation, passes a sanitiser first (and the
 * page's Content-Security-Policy forbids inline scripts in any case).
 */
"use strict";

(function (global) {
  // ------------------------------------------------------------------ DOM
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === null || v === undefined || v === false) continue;
        if (k === "class") el.className = v;
        else if (k === "text") el.textContent = v;
        else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
        else if (k === "style") el.setAttribute("style", v);
        else el.setAttribute(k, v === true ? "" : v);
      }
    }
    for (const k of kids.flat()) {
      if (k === null || k === undefined || k === false) continue;
      el.appendChild(typeof k === "string" || typeof k === "number" ? document.createTextNode(String(k)) : k);
    }
    return el;
  }
  const SVGNS = "http://www.w3.org/2000/svg";
  function s(tag, attrs, ...kids) {
    const el = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined) continue;
      if (k === "text") el.textContent = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v);
    }
    for (const k of kids.flat()) if (k) el.appendChild(k);
    return el;
  }
  const fmt = (x, d = 0) => Number(x).toLocaleString("sk-SK", { minimumFractionDigits: d, maximumFractionDigits: d });
  const LETTERS = "ABCDEFGH";

  function sanitizeSvg(markup) {
    const doc = new DOMParser().parseFromString(String(markup || ""), "image/svg+xml");
    const root = doc.documentElement;
    if (!root || root.nodeName.toLowerCase() !== "svg") return null;
    const bad = ["script", "foreignobject", "iframe", "object", "embed", "use"];
    const walk = (node) => {
      for (const child of Array.from(node.children)) {
        if (bad.includes(child.nodeName.toLowerCase())) { child.remove(); continue; }
        for (const at of Array.from(child.attributes)) {
          const n = at.name.toLowerCase();
          if (n.startsWith("on") || /javascript:/i.test(at.value) || n === "href" || n === "xlink:href") child.removeAttribute(at.name);
        }
        walk(child);
      }
    };
    for (const at of Array.from(root.attributes)) if (at.name.toLowerCase().startsWith("on")) root.removeAttribute(at.name);
    walk(root);
    return document.importNode(root, true);
  }

  // A small stats object every widget keeps; the app sends it with the
  // engagement event when the activity closes.
  function newStats() { return { steps: 0, plays: 0, predictions: 0, predictionsCorrect: 0 }; }

  function controls(buttons) {
    return h("div", { class: "w-controls" }, buttons);
  }

  // ============================================================ widgets
  // Every widget: (params, ctx) -> { el, stats, destroy }
  // ctx.onComplete(result) is called when the pupil has done what the widget asks.

  // ---------------------------------------------------- binary search
  function bsSteps(arr, target, mode) {
    const steps = [];
    if (mode === "linear") {
      steps.push({ lo: 0, hi: arr.length - 1, mid: null, cmp: null, n: 0,
        text: `Hľadáme ${target}. Lineárne vyhľadávanie porovnáva prvky jeden po druhom zľava.` });
      for (let i = 0; i < arr.length; i++) {
        const eq = arr[i] === target;
        steps.push({ lo: i, hi: arr.length - 1, mid: i, cmp: eq ? "eq" : "ne", n: i + 1,
          text: eq ? `A[${i}] = ${arr[i]} = ${target} → nájdené po ${i + 1} porovnaniach.`
                   : `A[${i}] = ${arr[i]} ≠ ${target} → pokračujeme ďalším prvkom.` });
        if (eq) return { steps, found: i };
      }
      steps.push({ lo: arr.length, hi: arr.length - 1, mid: null, cmp: "empty", n: arr.length,
        text: `Prešli sme celé pole (${arr.length} porovnaní) — ${target} v poli nie je.` });
      return { steps, found: -1 };
    }
    let lo = 0, hi = arr.length - 1, n = 0;
    steps.push({ lo, hi, mid: null, cmp: null, n,
      text: `Hľadáme ${target}. Na začiatku je interval celé pole: lavy = 0, pravy = ${hi}.` });
    while (lo <= hi) {
      const mid = Math.floor((lo + hi) / 2);
      const v = arr[mid];
      n += 1;
      if (v === target) {
        steps.push({ lo, hi, mid, cmp: "eq", n,
          text: `stred = ⌊(${lo} + ${hi}) / 2⌋ = ${mid}. A[${mid}] = ${v} = ${target} → nájdené po ${n} porovnaniach.` });
        return { steps, found: mid };
      }
      if (v < target) {
        steps.push({ lo, hi, mid, cmp: "lt", n,
          text: `stred = ⌊(${lo} + ${hi}) / 2⌋ = ${mid}. A[${mid}] = ${v} < ${target} → hľadaný prvok môže byť len vpravo: lavy = ${mid + 1}.` });
        lo = mid + 1;
      } else {
        steps.push({ lo, hi, mid, cmp: "gt", n,
          text: `stred = ⌊(${lo} + ${hi}) / 2⌋ = ${mid}. A[${mid}] = ${v} > ${target} → hľadaný prvok môže byť len vľavo: pravy = ${mid - 1}.` });
        hi = mid - 1;
      }
    }
    steps.push({ lo, hi, mid: null, cmp: "empty", n,
      text: `lavy = ${lo} > pravy = ${hi} → interval je prázdny, ${target} v poli nie je (${n} porovnaní).` });
    return { steps, found: -1 };
  }

  function binarySearch(params, ctx) {
    const arr = params.array, target = params.target, mode = params.mode || "binary";
    const predict = !!params.predict;
    const { steps, found } = bsSteps(arr, target, mode);
    const stats = newStats();
    let i = 0, timer = null, awaiting = false, completed = false;

    const cells = arr.map((v, k) => h("div", { class: "cell", "data-k": k },
      h("span", { class: "idx", text: String(k) }), h("span", { text: String(v) })));
    const ptrs = arr.map(() => h("span"));
    const caption = h("p", { class: "w-caption", "aria-live": "polite" });
    const counter = h("span", { class: "w-stat" });
    const btnBack = h("button", { class: "btn btn-secondary btn-sm", type: "button", onclick: () => go(i - 1) }, "◀ Späť");
    const btnNext = h("button", { class: "btn btn-primary btn-sm", type: "button", onclick: () => next() }, "Ďalej ▶");
    const btnPlay = h("button", { class: "btn btn-secondary btn-sm", type: "button", onclick: () => toggle() }, "▶ Prehrať");
    const btnShow = h("button", { class: "btn btn-ghost btn-sm", type: "button", hidden: true, onclick: () => { awaiting = false; go(i + 1); } }, "Neviem, ukáž");
    const btnReset = h("button", { class: "btn btn-ghost btn-sm", type: "button", onclick: () => { stop(); go(0); } }, "↺ Znova");

    cells.forEach((c, k) => c.addEventListener("click", () => pick(k)));

    const el = h("div", { class: "widget" },
      h("div", { class: "row", style: "justify-content:space-between;margin-bottom:10px" },
        h("span", { class: "chip chip-soft", text: (mode === "linear" ? "Lineárne" : "Binárne") + ` vyhľadávanie · hľadáme ${target}` }),
        h("span", { class: "small muted" }, "Porovnaní: ", counter)),
      h("div", { class: "cells", role: "list" }, cells),
      h("div", { class: "ptrs", "aria-hidden": "true" }, ptrs),
      caption,
      controls([btnBack, btnNext, btnShow, btnPlay, btnReset]));

    function paint() {
      const st = steps[i];
      cells.forEach((c, k) => {
        c.className = "cell";
        const inRange = k >= st.lo && k <= st.hi;
        if (mode === "linear") { if (st.mid !== null && k < st.mid) c.classList.add("out"); }
        else if (!inRange || st.cmp === "empty") c.classList.add("out");
        if (st.mid === k) c.classList.add(st.cmp === "eq" ? "found" : "mid");
      });
      ptrs.forEach((p, k) => {
        const tags = [];
        if (mode !== "linear" && st.cmp !== "empty") {
          if (k === st.lo) tags.push("L");
          if (k === st.mid) tags.push("S");
          if (k === st.hi) tags.push("P");
        } else if (k === st.mid) tags.push("↑");
        p.textContent = tags.join(" ");
      });
      caption.textContent = st.text;
      counter.textContent = String(st.n);
      btnBack.disabled = i === 0;
      btnNext.disabled = i >= steps.length - 1;
      if (i >= steps.length - 1 && !completed) {
        completed = true;
        ctx.onComplete && ctx.onComplete({ completed: true, value: st.n, found: found >= 0,
          predictions: stats.predictions, predictionsCorrect: stats.predictionsCorrect });
      }
    }
    function go(k) {
      i = Math.max(0, Math.min(steps.length - 1, k));
      awaiting = false; btnShow.hidden = true;
      paint();
    }
    function next() {
      if (i >= steps.length - 1) return;
      stats.steps++;
      const nxt = steps[i + 1];
      if (predict && nxt.mid !== null && !awaiting) {
        // ask before revealing: which element is compared now?
        awaiting = true;
        btnShow.hidden = false;
        stop();
        caption.textContent = "Ktorý prvok sa porovná teraz? Klikni naň.";
        cells.forEach((c, k) => { if (k >= nxt.lo && k <= nxt.hi) c.classList.add("pickable"); });
        return;
      }
      go(i + 1);
    }
    function pick(k) {
      if (!awaiting) return;
      const nxt = steps[i + 1];
      stats.predictions++;
      if (k === nxt.mid) {
        stats.predictionsCorrect++;
        go(i + 1);
        caption.textContent = "✓ Správne! " + caption.textContent;
      } else {
        cells[k].classList.add("wrong");
        caption.textContent = `Nie, porovná sa A[${nxt.mid}] = ${arr[nxt.mid]}. ` +
          (mode === "linear" ? "Lineárne vyhľadávanie ide po poradí." : `Stred intervalu ⟨${nxt.lo}, ${nxt.hi}⟩ je ⌊(${nxt.lo}+${nxt.hi})/2⌋ = ${nxt.mid}.`);
        awaiting = false; btnShow.hidden = true;
        setTimeout(() => { i = i + 1; paint(); caption.textContent = `Nie, porovná sa A[${nxt.mid}]. ` + steps[i].text; }, 900);
      }
    }
    function toggle() { if (timer) stop(); else play(); }
    function play() {
      stats.plays++;
      if (i >= steps.length - 1) go(0);
      btnPlay.textContent = "❚❚ Pauza";
      timer = setInterval(() => { if (i >= steps.length - 1 || awaiting) stop(); else next(); }, 1600);
    }
    function stop() { if (timer) clearInterval(timer); timer = null; btnPlay.textContent = "▶ Prehrať"; }
    paint();
    return { el, stats, destroy: stop };
  }

  // ------------------------------------------------------- search race
  function searchRace(params, ctx) {
    const stats = newStats();
    let n = params.start || 16;
    const tried = new Set();
    const input = h("input", { type: "number", min: "1", max: "1000000000", value: String(n), style: "max-width:200px", "aria-label": "Veľkosť poľa n" });
    const linBar = h("i"), binBar = h("i");
    const linVal = h("b"), binVal = h("b");
    const note = h("p", { class: "w-caption", "aria-live": "polite" });
    const el = h("div", { class: "widget" },
      h("label", { text: "Veľkosť poľa n" }),
      h("div", { class: "row" }, input,
        ...[["÷10", 0.1], ["÷2", 0.5], ["×2", 2], ["×10", 10]].map(([t, f]) =>
          h("button", { class: "btn btn-secondary btn-sm", type: "button", onclick: () => set(Math.round(n * f), t) }, t))),
      h("div", { class: "race" },
        h("div", { class: "race-row" }, h("div", { class: "race-label" }, h("span", { text: "Lineárne vyhľadávanie (najhorší prípad)" }), linVal), h("div", { class: "race-track" }, linBar)),
        h("div", { class: "race-row bin" }, h("div", { class: "race-label" }, h("span", { text: "Binárne vyhľadávanie (najhorší prípad)" }), binVal), h("div", { class: "race-track" }, binBar))),
      note);
    input.addEventListener("change", () => set(parseInt(input.value, 10) || 1, "input"));
    const lin = (x) => x, bin = (x) => Math.floor(Math.log2(x)) + 1;
    function set(x, how) {
      const prev = n;
      n = Math.max(1, Math.min(1e9, x));
      input.value = String(n);
      stats.steps++;
      tried.add(n);
      paint();
      // data only, no interpretation: drawing the conclusion is the pupil's job
      // (and the delayed test asks for it in words)
      if (prev !== n) note.textContent = `n: ${fmt(prev)} → ${fmt(n)}   ·   lineárne: ${fmt(lin(prev))} → ${fmt(lin(n))}   ·   binárne: ${bin(prev)} → ${bin(n)}`;
      if (tried.size >= 3 && ctx.onComplete) ctx.onComplete({ completed: true, value: n });
    }
    function paint() {
      linVal.textContent = fmt(lin(n));
      binVal.textContent = fmt(bin(n));
      linBar.style.width = "100%";
      binBar.style.width = Math.max(0.6, 100 * bin(n) / lin(n)) + "%";
      if (!note.textContent) note.textContent = "Skús n zdvojnásobiť alebo zväčšiť desaťkrát a sleduj, ako sa mení počet porovnaní.";
    }
    paint();
    return { el, stats, destroy() {} };
  }

  // ------------------------------------------------------ guess number
  function guessNumber(params, ctx) {
    const max = params.max || 100;
    const optimal = Math.ceil(Math.log2(max + 1));
    const stats = newStats();
    let secret, lo, hi, guesses;
    const input = h("input", { type: "number", min: "1", max: String(max), inputmode: "numeric", style: "max-width:160px", "aria-label": "Tvoj tip" });
    const btn = h("button", { class: "btn btn-primary", type: "button" }, "Tipni");
    const msg = h("p", { class: "w-caption", "aria-live": "polite" });
    const range = h("i");
    const log = h("div", { class: "guess-log" });
    const again = h("button", { class: "btn btn-secondary btn-sm", type: "button", hidden: true }, "Hrať znova");
    const el = h("div", { class: "widget" },
      h("p", { text: `Počítač si myslí číslo od 1 do ${max}. Po každom tipe ti povie, či je hľadané číslo väčšie alebo menšie.` }),
      h("div", { class: "range-bar", "aria-hidden": "true" }, range),
      h("div", { class: "row small muted", style: "justify-content:space-between" }, h("span", { text: "1" }), h("span", { text: String(max) })),
      h("div", { class: "row", style: "margin-top:10px" }, input, btn, again),
      msg, log);
    function reset() {
      secret = 1 + Math.floor(Math.random() * max);
      lo = 1; hi = max; guesses = 0; log.innerHTML = "";
      msg.textContent = "Zadaj prvý tip."; again.hidden = true; btn.disabled = false; input.disabled = false;
      input.value = ""; paint();
    }
    function paint() {
      range.style.left = (100 * (lo - 1) / max) + "%";
      range.style.width = (100 * (hi - lo + 1) / max) + "%";
    }
    function guess() {
      const g = parseInt(input.value, 10);
      if (!(g >= 1 && g <= max)) { msg.textContent = `Zadaj celé číslo od 1 do ${max}.`; return; }
      guesses++; stats.steps++;
      let chip;
      if (g === secret) {
        msg.textContent = `Uhádol/a si na ${guesses} ${guesses === 1 ? "pokus" : guesses < 5 ? "pokusy" : "pokusov"}! ` +
          `Ak vždy tipneš stred zostávajúceho intervalu, stačí najviac ${optimal} pokusov — to je binárne vyhľadávanie.`;
        chip = h("span", { class: "chip chip-good", text: `${g} ✓` });
        lo = hi = g; btn.disabled = true; input.disabled = true; again.hidden = false;
        ctx.onComplete && ctx.onComplete({ completed: true, value: guesses, optimal });
      } else if (g < secret) {
        msg.textContent = `Hľadané číslo je VÄČŠIE ako ${g}.`; lo = Math.max(lo, g + 1);
        chip = h("span", { class: "chip chip-soft", text: `${g} ↑` });
      } else {
        msg.textContent = `Hľadané číslo je MENŠIE ako ${g}.`; hi = Math.min(hi, g - 1);
        chip = h("span", { class: "chip chip-soft", text: `${g} ↓` });
      }
      log.appendChild(chip); paint(); input.value = ""; input.focus();
    }
    btn.addEventListener("click", guess);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") guess(); });
    again.addEventListener("click", () => { stats.plays++; reset(); });
    reset();
    return { el, stats, destroy() {} };
  }

  // ---------------------------------------------------------- interest
  function interest(params, ctx) {
    const stats = newStats();
    let K0 = params.principal || 1000, p = params.rate || 5, years = params.years || 20;
    let shown = years, timer = null, done = false;
    const chart = s("svg", { class: "chart", viewBox: "0 0 640 260", role: "img", "aria-label": "Graf rastu sumy" });
    const kv = h("div", { class: "kv" });
    const rateOut = h("output", { class: "value" }), yearsOut = h("output", { class: "value" });
    const rate = h("input", { type: "range", min: "1", max: "20", step: "0.5", value: String(p), "aria-label": "Úroková miera" });
    const yrs = h("input", { type: "range", min: "1", max: "40", step: "1", value: String(years), "aria-label": "Počet rokov" });
    const k0 = h("input", { type: "number", min: "1", value: String(K0), style: "max-width:160px", "aria-label": "Počiatočný vklad" });
    const btnPlay = h("button", { class: "btn btn-primary btn-sm", type: "button" }, "▶ Prehrať rok po roku");
    const note = h("p", { class: "w-caption", "aria-live": "polite" });
    const el = h("div", { class: "widget" },
      h("div", { class: "sliders" },
        h("div", {}, h("label", {}, "Vklad K₀ (€)"), k0),
        h("div", {}, h("label", {}, "Úroková miera p: ", rateOut, " %"), rate),
        h("div", {}, h("label", {}, "Počet rokov n: ", yearsOut), yrs)),
      chart,
      h("div", { class: "legend" },
        h("span", {}, h("i", { style: "background:var(--warn)" }), "jednoduché úročenie  K₀·(1 + n·p)"),
        h("span", {}, h("i", { style: "background:var(--primary)" }), "zložené úročenie  K₀·(1 + p)ⁿ")),
      kv, note, controls([btnPlay]));
    const simple = (n) => K0 * (1 + n * p / 100);
    const comp = (n) => K0 * Math.pow(1 + p / 100, n);
    function paint() {
      rateOut.textContent = fmt(p, p % 1 ? 1 : 0); yearsOut.textContent = String(years);
      while (chart.firstChild) chart.removeChild(chart.firstChild);
      const W = 640, H = 260, L = 56, B = 28, T = 12, R = 10;
      const maxV = comp(years) * 1.05;
      const bw = (W - L - R) / years;
      chart.appendChild(s("line", { class: "axis", x1: L, y1: H - B, x2: W - R, y2: H - B }));
      chart.appendChild(s("line", { class: "axis", x1: L, y1: T, x2: L, y2: H - B }));
      for (let t = 0; t <= 4; t++) {
        const v = maxV * t / 4, y = H - B - (H - B - T) * t / 4;
        chart.appendChild(s("text", { x: L - 6, y: y + 4, "text-anchor": "end", text: fmt(v) }));
      }
      for (let n = 1; n <= years; n++) {
        const x = L + (n - 1) * bw;
        const hs = (H - B - T) * simple(n) / maxV, hc = (H - B - T) * comp(n) / maxV;
        const vis = n <= shown ? 1 : 0.08;
        chart.appendChild(s("rect", { class: "simple", x: x + bw * 0.12, y: H - B - hs, width: bw * 0.36, height: hs, rx: 2, opacity: vis }));
        chart.appendChild(s("rect", { class: "compound", x: x + bw * 0.52, y: H - B - hc, width: bw * 0.36, height: hc, rx: 2, opacity: vis }));
        if (years <= 20 || n % 5 === 0) chart.appendChild(s("text", { x: x + bw / 2, y: H - 10, "text-anchor": "middle", text: String(n) }));
      }
      const n = Math.max(1, shown);
      const dbl = Math.log(2) / Math.log(1 + p / 100);
      kv.innerHTML = "";
      [[fmt(simple(n), 2) + " €", `jednoduché po ${n} r.`], [fmt(comp(n), 2) + " €", `zložené po ${n} r.`],
       [fmt(comp(n) - simple(n), 2) + " €", "rozdiel"], [`≈ ${fmt(72 / p, 1)} r.`, "zdvojnásobenie podľa pravidla 72"],
       [`${fmt(dbl, 1)} r.`, "zdvojnásobenie presne"]].forEach(([b, t]) => kv.appendChild(h("div", {}, h("b", { text: b }), h("span", { text: t }))));
    }
    function changed() {
      K0 = Math.max(1, parseFloat(k0.value) || 1); p = parseFloat(rate.value); years = parseInt(yrs.value, 10);
      shown = years; stats.steps++; paint(); maybeDone();
    }
    function maybeDone() {
      if (!done && stats.steps + stats.plays >= 3) { done = true; ctx.onComplete && ctx.onComplete({ completed: true, value: Math.round(comp(years)) }); }
    }
    [rate, yrs, k0].forEach((x) => x.addEventListener("input", changed));
    btnPlay.addEventListener("click", () => {
      if (timer) { clearInterval(timer); timer = null; btnPlay.textContent = "▶ Prehrať rok po roku"; return; }
      stats.plays++; shown = 0; paint(); btnPlay.textContent = "❚❚ Pauza";
      timer = setInterval(() => {
        shown++; paint();
        const d = comp(shown) - simple(shown);
        note.textContent = `Rok ${shown}: zložené úročenie je o ${fmt(d, 2)} € vyššie — úrok sa počíta aj z minuloročných úrokov.`;
        if (shown >= years) { clearInterval(timer); timer = null; btnPlay.textContent = "▶ Prehrať znova"; maybeDone(); }
      }, Math.max(120, 2400 / years));
    });
    paint();
    note.textContent = "Posuň úrokovú mieru alebo počet rokov, alebo prehraj rast rok po roku.";
    return { el, stats, destroy() { if (timer) clearInterval(timer); } };
  }

  // ------------------------------------------------------------ circuit
  function circuit(params, ctx) {
    const stats = newStats();
    const U = params.voltage || 12, R = params.resistance || 6;
    const mode = params.mode || "compare";
    let n = params.bulbs || 2;
    const broken = { series: new Set(), parallel: new Set() };
    let done = false;
    const holder = h("div", { class: "row", style: "align-items:stretch;gap:14px" });
    const minus = h("button", { class: "btn btn-secondary btn-sm", type: "button" }, "− žiarovka");
    const plus = h("button", { class: "btn btn-secondary btn-sm", type: "button" }, "+ žiarovka");
    const fix = h("button", { class: "btn btn-ghost btn-sm", type: "button" }, "Opraviť všetky");
    const note = h("p", { class: "w-caption", "aria-live": "polite" });
    const el = h("div", { class: "widget circuit" },
      h("p", { class: "small muted", text: `Zdroj ${U} V, každá žiarovka má odpor ${R} Ω. Kliknutím na žiarovku ju „vyskrutkuješ“ (vyhorí).` }),
      holder, note, controls([minus, plus, fix]));
    function solve(kind) {
      const ok = []; for (let k = 0; k < n; k++) ok.push(!broken[kind].has(k));
      if (kind === "series") {
        const closed = ok.every(Boolean);
        const I = closed ? U / (n * R) : 0;
        return { I, P: ok.map(() => I * I * R) };
      }
      const P = ok.map((o) => (o ? U * U / R : 0));
      const I = ok.filter(Boolean).length * U / R;
      return { I, P };
    }
    function draw(kind) {
      const W = 340, H = 230, x0 = 58, x1 = W - 20, y0 = 50, y1 = H - 30;
      const sol = solve(kind);
      const Pmax = U * U / R;
      const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": kind === "series" ? "Sériové zapojenie" : "Paralelné zapojenie" });
      const live = sol.I > 0;
      const wire = (d) => svg.appendChild(s("path", { class: "wire" + (live ? " live" : ""), d }));
      // battery on the left side
      const by = (y0 + y1) / 2;
      wire(`M${x0} ${y0} V${by - 14} M${x0} ${by + 14} V${y1}`);
      svg.appendChild(s("line", { class: "battery", x1: x0 - 14, y1: by - 8, x2: x0 + 14, y2: by - 8 }));
      svg.appendChild(s("line", { class: "battery", x1: x0 - 7, y1: by + 8, x2: x0 + 7, y2: by + 8 }));
      svg.appendChild(s("text", { x: x0 - 20, y: by + 4, "text-anchor": "end", text: `${U} V` }));
      const bulbAt = (k, cx, cy) => {
        const g = s("g", {});
        const glow = Math.sqrt(sol.P[k] / Pmax);
        if (glow > 0) g.appendChild(s("circle", { class: "bulb-glow", cx, cy, r: 14 + 16 * glow, opacity: 0.18 + 0.6 * glow }));
        const glass = s("circle", { class: "bulb-glass", cx, cy, r: 14, tabindex: "0", role: "button",
          "aria-label": `Žiarovka ${k + 1}${broken[kind].has(k) ? " (vyhorená)" : ""}` });
        const toggle = () => { if (broken[kind].has(k)) broken[kind].delete(k); else broken[kind].add(k); stats.steps++; repaint(`${kind === "series" ? "Sériovo" : "Paralelne"}: žiarovka ${k + 1} ${broken[kind].has(k) ? "vyhorela" : "znova svieti"}.`); };
        glass.addEventListener("click", toggle);
        glass.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
        g.appendChild(glass);
        if (broken[kind].has(k)) {
          g.appendChild(s("path", { class: "bulb-broken", d: `M${cx - 8} ${cy - 8} L${cx + 8} ${cy + 8} M${cx + 8} ${cy - 8} L${cx - 8} ${cy + 8}` }));
        } else {
          g.appendChild(s("path", { class: "wire", d: `M${cx - 6} ${cy + 4} q3 -10 6 0 q3 10 6 0`, style: "stroke-width:1.6" }));
        }
        const pct = `${Math.round(100 * sol.P[k] / Pmax)} %`;
        // under the bulb on the series rail, beside it on a vertical branch
        if (kind === "series") g.appendChild(s("text", { x: cx, y: cy + 34, "text-anchor": "middle", text: pct }));
        else g.appendChild(s("text", { x: cx + 19, y: cy + 4, "text-anchor": "start", text: pct }));
        svg.appendChild(g);
      };
      if (kind === "series") {
        const xs = []; for (let k = 0; k < n; k++) xs.push(x0 + 50 + (x1 - x0 - 80) * (n === 1 ? 0.5 : k / (n - 1)));
        let d = `M${x0} ${y0}`;
        xs.forEach((x) => { d += ` H${x - 14} M${x + 14} ${y0}`; });
        d += ` H${x1} V${y1} H${x0}`;
        wire(d);
        if (live) svg.appendChild(s("path", { class: "flow", d: `M${x0} ${y1} V${y0} H${x1} V${y1} Z` }));
        xs.forEach((x, k) => bulbAt(k, x, y0));
      } else {
        wire(`M${x0} ${y0} H${x1} M${x0} ${y1} H${x1}`);
        for (let k = 0; k < n; k++) {
          const x = x0 + 40 + (x1 - x0 - 100) * (n === 1 ? 0.5 : k / (n - 1));
          const cy = (y0 + y1) / 2;
          wire(`M${x} ${y0} V${cy - 14} M${x} ${cy + 14} V${y1}`);
          if (!broken.parallel.has(k)) svg.appendChild(s("path", { class: "flow", d: `M${x} ${y0} V${y1}` }));
          bulbAt(k, x, cy);
        }
      }
      svg.appendChild(s("text", { x: W - 20, y: 24, "text-anchor": "end", text: `I = ${fmt(sol.I, 2)} A` }));
      return h("div", { class: "card card-pad", style: "flex:1;min-width:250px;padding:12px" },
        h("div", { class: "row", style: "justify-content:space-between" },
          h("strong", { text: kind === "series" ? "Sériové zapojenie" : "Paralelné zapojenie" }),
          h("span", { class: "small muted", text: kind === "series" ? `R = ${n}·${R} = ${n * R} Ω` : `R = ${R}/${n} = ${fmt(R / n, 2)} Ω` })),
        svg);
    }
    function repaint(msg) {
      holder.innerHTML = "";
      if (mode !== "parallel") holder.appendChild(draw("series"));
      if (mode !== "series") holder.appendChild(draw("parallel"));
      minus.disabled = n <= 1; plus.disabled = n >= 4;
      if (msg) note.textContent = msg;
      if (!done && stats.steps >= 2) { done = true; ctx.onComplete && ctx.onComplete({ completed: true, value: n }); }
    }
    minus.addEventListener("click", () => { n--; broken.series.clear(); broken.parallel.clear(); stats.steps++; repaint(`Počet žiaroviek: ${n}.`); });
    plus.addEventListener("click", () => { n++; broken.series.clear(); broken.parallel.clear(); stats.steps++; repaint(`Počet žiaroviek: ${n}. Sleduj jas a celkový prúd.`); });
    fix.addEventListener("click", () => { broken.series.clear(); broken.parallel.clear(); stats.steps++; repaint("Všetky žiarovky svietia."); });
    repaint("Pridaj žiarovku alebo jednu vyskrutkuj a porovnaj obe zapojenia.");
    return { el, stats, destroy() {} };
  }

  // ------------------------------------------------------------- frames
  function frames(params, ctx) {
    const list = params.frames || [];
    const stats = newStats();
    let i = 0, timer = null, completed = false;
    const stage = h("div", { class: "frames-stage", "aria-live": "polite" });
    const dots = h("div", { class: "frames-dots", "aria-hidden": "true" }, list.map(() => h("i")));
    const back = h("button", { class: "btn btn-secondary btn-sm", type: "button", onclick: () => go(i - 1) }, "◀ Späť");
    const fwd = h("button", { class: "btn btn-primary btn-sm", type: "button", onclick: () => { stats.steps++; go(i + 1); } }, "Ďalej ▶");
    const play = h("button", { class: "btn btn-secondary btn-sm", type: "button" }, "▶ Prehrať");
    const el = h("div", { class: "widget" }, stage, dots, controls([back, fwd, play]));
    function go(k) {
      i = Math.max(0, Math.min(list.length - 1, k));
      const f = list[i];
      stage.innerHTML = "";
      if (f.title) stage.appendChild(h("h3", { text: f.title }));
      if (f.svg) { const node = sanitizeSvg(f.svg); if (node) stage.appendChild(node); }
      if (f.text) stage.appendChild(h("p", { text: f.text }));
      Array.from(dots.children).forEach((d, k2) => d.classList.toggle("on", k2 === i));
      back.disabled = i === 0; fwd.disabled = i === list.length - 1;
      if (i === list.length - 1 && !completed) { completed = true; ctx.onComplete && ctx.onComplete({ completed: true, value: list.length }); }
    }
    play.addEventListener("click", () => {
      if (timer) { clearInterval(timer); timer = null; play.textContent = "▶ Prehrať"; return; }
      stats.plays++; if (i >= list.length - 1) go(0);
      play.textContent = "❚❚ Pauza";
      timer = setInterval(() => { if (i >= list.length - 1) { clearInterval(timer); timer = null; play.textContent = "▶ Prehrať"; } else { stats.steps++; go(i + 1); } }, params.interval || 2600);
    });
    go(0);
    return { el, stats, destroy() { if (timer) clearInterval(timer); } };
  }

  const WIDGETS = { "binary-search": binarySearch, "search-race": searchRace, "guess-number": guessNumber,
                    "interest": interest, "circuit": circuit, "frames": frames };

  function mountWidget(a, ctx) {
    const make = WIDGETS[a.widget];
    if (!make) return { el: h("p", { class: "muted", text: `Neznámy widget: ${a.widget}` }), stats: newStats(), destroy() {} };
    return make(a.params || {}, ctx);
  }

  // =========================================================== activities
  const TYPE_LABELS = { poll: "Rýchla otázka", predict: "Predpoveď", order: "Zoraď kroky",
                        animation: "Animácia", handson: "Praktická úloha", reflect: "Reflexia" };

  function confidenceBlock(label) {
    const out = h("output", { class: "value", text: "—" });
    const range = h("input", { type: "range", min: "0", max: "100", step: "5", value: "50", class: "unset", "aria-label": label });
    let touched = false;
    const mark = () => { touched = true; range.classList.remove("unset"); out.textContent = range.value + " %"; };
    range.addEventListener("input", mark);
    range.addEventListener("change", mark);
    const el = h("div", { style: "margin-top:16px" },
      h("label", {}, label + " ", out), range,
      h("div", { class: "slider-scale" }, h("span", { text: "0 %" }), h("span", { text: "100 %" })));
    return { el, value: () => (touched ? parseInt(range.value, 10) : null), set(v) { if (v !== null && v !== undefined) { range.value = String(v); mark(); } }, disable() { range.disabled = true; } };
  }

  function resultBars(labels, counts, key) {
    const total = counts.reduce((a, b) => a + b, 0) || 1;
    return h("div", { class: "result-bars" }, labels.map((lab, k) =>
      h("div", { class: "result-row" + (k === key ? " correct" : "") },
        h("div", {},
          h("div", { class: "result-label" }, h("strong", { text: LETTERS[k] }), h("span", { text: lab }), k === key ? h("span", { class: "chip chip-good", text: "správne" }) : null),
          h("div", { class: "result-track" }, h("i", { style: `width:${(100 * counts[k] / total).toFixed(1)}%` }))),
        h("div", { class: "result-n", text: String(counts[k]) }))));
  }

  function footer(btnLabel) {
    const status = h("span", { class: "act-status", role: "status" });
    const btn = h("button", { class: "btn btn-primary", type: "button" }, btnLabel);
    return { el: h("div", { class: "act-footer" }, btn, status), btn, status };
  }

  async function doSubmit(io, f, payload, okText) {
    f.btn.disabled = true;
    f.status.className = "act-status";
    f.status.textContent = "Odosielam…";
    try {
      const res = await io.submit(payload);
      f.status.className = "act-status good";
      f.status.textContent = okText || "Odoslané ✓  Môžeš zmeniť, kým učiteľ nezverejní výsledky.";
      return res;
    } catch (e) {
      f.status.className = "act-status";
      f.status.textContent = e.message || "Nepodarilo sa odoslať.";
      throw e;
    } finally {
      f.btn.disabled = false;
    }
  }

  function optionButtons(opts, onPick) {
    let chosen = null;
    const btns = opts.map((o, k) => h("button", { class: "option", type: "button", "aria-pressed": "false",
      onclick: () => { chosen = k; btns.forEach((b, j) => b.setAttribute("aria-pressed", j === k ? "true" : "false")); onPick && onPick(k); } },
      h("span", { class: "letter", text: LETTERS[k] }), h("span", { class: "bar", text: o })));
    return { el: h("div", { class: "options", role: "group" }, btns), get: () => chosen,
             set(k) { if (k !== null && k !== undefined && btns[k]) btns[k].click(); },
             disable() { btns.forEach((b) => (b.disabled = true)); } };
  }

  // --------------------------------------------------------------- poll
  function renderPoll(root, view, io) {
    const a = view.activity;
    root.appendChild(h("p", { class: "act-question", text: a.question }));
    if (view.revealed && view.results) {
      root.appendChild(resultBars(a.options, view.results.counts || a.options.map(() => 0), a.key));
      if (view.mine) root.appendChild(h("p", { class: "small muted", style: "margin-top:12px", text: `Tvoja odpoveď: ${LETTERS[view.mine.choice]}` + (a.key !== undefined ? (view.mine.correct ? " — správne ✓" : " — nesprávne") : "") }));
      if (a.explain) root.appendChild(h("div", { class: "callout callout-good explain-box", text: a.explain }));
      return {};
    }
    const opts = optionButtons(a.options);
    root.appendChild(opts.el);
    const conf = a.confidence ? confidenceBlock("Nakoľko si si istý/á svojou odpoveďou?") : null;
    if (conf) root.appendChild(conf.el);
    const f = footer("Odoslať odpoveď");
    root.appendChild(f.el);
    if (view.mine) { opts.set(view.mine.choice); if (conf) conf.set(view.mine.confidence); f.status.className = "act-status good"; f.status.textContent = "Odoslané ✓  Môžeš zmeniť, kým učiteľ nezverejní výsledky."; }
    f.btn.addEventListener("click", () => {
      if (opts.get() === null) { f.status.textContent = "Najprv vyber jednu možnosť."; return; }
      if (conf && conf.value() === null) { f.status.textContent = "Posuň posuvník istoty."; return; }
      doSubmit(io, f, { choice: opts.get(), confidence: conf ? conf.value() : undefined }).catch(() => {});
    });
    return {};
  }

  // ------------------------------------------------------------ predict
  function renderPredict(root, view, io) {
    const a = view.activity;
    const kind = a.input.kind;
    root.appendChild(h("p", { class: "act-question", text: a.question }));
    let widget = null;
    const observe = h("div", { style: "margin-top:18px" });
    const showObserve = () => {
      if (!a.widget || widget) return;
      observe.appendChild(h("h3", { style: "margin-bottom:10px", text: "Pozri sa, čo sa naozaj stane:" }));
      widget = mountWidget(a, { onComplete: () => {} });
      observe.appendChild(widget.el);
    };
    if (view.revealed && view.results) {
      const res = view.results;
      if (kind === "choice") root.appendChild(resultBars(a.input.options, res.counts || [], a.answer));
      else root.appendChild(h("div", { class: "kv" },
        h("div", {}, h("b", { text: a.answer !== undefined ? fmt(a.answer, a.answer % 1 ? 2 : 0) : "—" }), h("span", { text: "správna hodnota" })),
        h("div", {}, h("b", { text: res.median !== undefined ? fmt(res.median, 2) : "—" }), h("span", { text: "medián triedy" })),
        h("div", {}, h("b", { text: view.mine ? fmt(view.mine.value, 2) : "—" }), h("span", { text: "tvoja predpoveď" }))));
      if (a.explain) root.appendChild(h("div", { class: "callout callout-good explain-box", text: a.explain }));
      root.appendChild(observe); showObserve();
      return { stats: () => (widget ? widget.stats : null), destroy: () => widget && widget.destroy() };
    }
    let opts = null, num = null;
    if (kind === "choice") { opts = optionButtons(a.input.options); root.appendChild(opts.el); }
    else {
      num = h("input", { type: "number", step: "any", inputmode: "decimal", style: "max-width:240px", "aria-label": "Tvoja predpoveď" });
      root.appendChild(h("div", {}, h("label", { text: "Tvoja predpoveď" + (a.input.unit ? ` (${a.input.unit})` : "") }), num));
    }
    const conf = a.confidence ? confidenceBlock("Nakoľko si si istý/á predpoveďou?") : null;
    if (conf) root.appendChild(conf.el);
    const f = footer("Odoslať predpoveď");
    root.appendChild(f.el);
    const why = h("textarea", { rows: "3", placeholder: "Prečo to tak je? Napíš jednou-dvoma vetami (nepovinné)." });
    const whyBtn = h("button", { class: "btn btn-secondary btn-sm", type: "button" }, "Odoslať vysvetlenie");
    const whyBox = h("div", { class: "explain-box", hidden: true }, h("label", { text: a.explain_prompt || "Vysvetli, čo si videl/a" }), why, h("div", { class: "actions" }, whyBtn));
    root.appendChild(observe); root.appendChild(whyBox);
    const payload = () => kind === "choice"
      ? { choice: opts.get(), confidence: conf ? conf.value() : undefined }
      : { value: num.value === "" ? null : Number(num.value), confidence: conf ? conf.value() : undefined };
    if (view.mine) {
      if (opts) opts.set(view.mine.choice); else num.value = String(view.mine.value);
      if (conf) conf.set(view.mine.confidence);
      f.status.className = "act-status good"; f.status.textContent = "Predpoveď odoslaná ✓";
      showObserve(); whyBox.hidden = false; if (view.mine.text) why.value = view.mine.text;
    }
    f.btn.addEventListener("click", () => {
      const p = payload();
      if (kind === "choice" && p.choice === null) { f.status.textContent = "Najprv vyber svoju predpoveď."; return; }
      if (kind === "number" && (p.value === null || !isFinite(p.value))) { f.status.textContent = "Zadaj číslo."; return; }
      if (conf && conf.value() === null) { f.status.textContent = "Posuň posuvník istoty."; return; }
      doSubmit(io, f, p, "Predpoveď odoslaná ✓").then(() => { showObserve(); whyBox.hidden = false; }).catch(() => {});
    });
    whyBtn.addEventListener("click", () => {
      const p = payload(); p.text = why.value.trim();
      if (!p.text) return;
      whyBtn.disabled = true;
      io.submit(p).then(() => { whyBtn.textContent = "Vysvetlenie odoslané ✓"; }).catch((e) => { whyBtn.textContent = e.message || "Chyba"; }).finally(() => { whyBtn.disabled = false; });
    });
    return { stats: () => (widget ? widget.stats : null), destroy: () => widget && widget.destroy() };
  }

  // -------------------------------------------------------------- order
  function renderOrder(root, view, io) {
    const a = view.activity;
    root.appendChild(h("p", { class: "act-question", text: a.question }));
    let order = (view.mine && view.mine.order) ? view.mine.order.slice() : (a.display || a.items.map((_, k) => k)).slice();
    const list = h("ol", { class: "order-list" });
    root.appendChild(list);
    const locked = !!view.revealed;
    let dragFrom = null;
    function paint() {
      list.innerHTML = "";
      order.forEach((item, pos) => {
        const li = h("li", { class: "order-item", draggable: locked ? "false" : "true", "data-pos": pos },
          h("span", { class: "pos", text: String(pos + 1) }),
          h("span", { class: "txt", text: a.items[item] }),
          locked ? null : h("span", { class: "mv" },
            h("button", { type: "button", "aria-label": "Posunúť vyššie", disabled: pos === 0, onclick: () => move(pos, pos - 1) }, "↑"),
            h("button", { type: "button", "aria-label": "Posunúť nižšie", disabled: pos === order.length - 1, onclick: () => move(pos, pos + 1) }, "↓")));
        if (locked) li.classList.add(item === pos ? "ok" : "no");
        li.addEventListener("dragstart", () => { dragFrom = pos; li.classList.add("dragging"); });
        li.addEventListener("dragend", () => li.classList.remove("dragging"));
        li.addEventListener("dragover", (e) => e.preventDefault());
        li.addEventListener("drop", (e) => { e.preventDefault(); if (dragFrom !== null) move(dragFrom, pos); dragFrom = null; });
        list.appendChild(li);
      });
    }
    function move(from, to) {
      if (to < 0 || to >= order.length || from === to) return;
      const [x] = order.splice(from, 1); order.splice(to, 0, x); paint();
    }
    paint();
    if (locked) {
      root.appendChild(h("h3", { style: "margin:18px 0 8px", text: "Správne poradie" }));
      root.appendChild(h("ol", { class: "order-list" }, a.items.map((t, k) => h("li", { class: "order-item ok" }, h("span", { class: "pos", text: String(k + 1) }), h("span", { class: "txt", text: t })))));
      if (view.results && view.results.score_mean !== undefined) root.appendChild(h("p", { class: "small muted", style: "margin-top:10px", text: `Trieda mala v priemere ${Math.round(100 * view.results.score_mean)} % položiek na správnom mieste.` }));
      return {};
    }
    const f = footer("Odoslať poradie");
    root.appendChild(f.el);
    if (view.mine) { f.status.className = "act-status good"; f.status.textContent = "Odoslané ✓  Môžeš ešte upraviť."; }
    f.btn.addEventListener("click", () => doSubmit(io, f, { order: order.slice() }).catch(() => {}));
    return {};
  }

  // ------------------------------------------------- animation / handson
  function renderWidgetActivity(root, view, io) {
    const a = view.activity;
    if (a.intro || a.question) root.appendChild(h("p", { class: "act-intro", text: a.intro || a.question }));
    let result = view.mine ? view.mine.result : null;
    const f = footer(a.type === "animation" ? "Hotovo" : "Odoslať výsledok");
    const answer = a.ask ? h("textarea", { rows: "2", placeholder: a.ask }) : null;
    const widget = mountWidget(a, { onComplete: (r) => { result = Object.assign({}, r); f.btn.disabled = false; f.status.textContent = "Môžeš odoslať."; } });
    root.appendChild(widget.el);
    if (answer) root.appendChild(h("div", { style: "margin-top:14px" }, h("label", { text: a.ask }), answer));
    root.appendChild(f.el);
    if (view.revealed) { f.btn.disabled = true; f.status.textContent = "Aktivita je uzavretá."; }
    else if (view.mine) { f.status.className = "act-status good"; f.status.textContent = "Odoslané ✓"; }
    else { f.btn.disabled = true; f.status.textContent = a.type === "animation" ? "Prejdi animáciu až do konca." : "Vyskúšaj si úlohu."; }
    f.btn.addEventListener("click", () => {
      const r = Object.assign({ completed: true }, result || {}, widget.stats ? { steps: widget.stats.steps } : {});
      const p = { result: r };
      if (answer && answer.value.trim()) p.text = answer.value.trim();
      doSubmit(io, f, p, "Odoslané ✓").catch(() => {});
    });
    return { stats: () => widget.stats, destroy: () => widget.destroy() };
  }

  // ------------------------------------------------------------ reflect
  function renderReflect(root, view, io) {
    const a = view.activity;
    root.appendChild(h("p", { class: "act-question", text: a.question }));
    const ta = h("textarea", { rows: "4", maxlength: "1000", placeholder: a.placeholder || "Napíš svoju odpoveď…" });
    root.appendChild(ta);
    const conf = a.confidence ? confidenceBlock(a.confidence_label || "Nakoľko dnešnej téme rozumieš?") : null;
    if (conf) root.appendChild(conf.el);
    const f = footer("Odoslať");
    root.appendChild(f.el);
    if (view.mine) { ta.value = view.mine.text || ""; if (conf) conf.set(view.mine.confidence); f.status.className = "act-status good"; f.status.textContent = "Odoslané ✓ Ďakujeme."; }
    if (view.revealed) { ta.disabled = true; f.btn.disabled = true; if (conf) conf.disable(); }
    f.btn.addEventListener("click", () => {
      if (!ta.value.trim() && !(conf && conf.value() !== null)) { f.status.textContent = "Napíš aspoň krátku odpoveď."; return; }
      if (conf && conf.value() === null) { f.status.textContent = "Posuň posuvník."; return; }
      doSubmit(io, f, { text: ta.value.trim(), confidence: conf ? conf.value() : undefined }, "Odoslané ✓ Ďakujeme.").catch(() => {});
    });
    return {};
  }

  const RENDERERS = { poll: renderPoll, predict: renderPredict, order: renderOrder,
                      animation: renderWidgetActivity, handson: renderWidgetActivity, reflect: renderReflect };

  function render(root, view, io) {
    root.innerHTML = "";
    const fn = RENDERERS[view.activity.type];
    if (!fn) { root.appendChild(h("p", { text: "Neznámy typ aktivity." })); return {}; }
    if (view.revealed) root.appendChild(h("div", { class: "callout callout-primary", style: "margin-bottom:16px", text: "Učiteľ zverejnil výsledky triedy." }));
    return fn(root, view, io) || {};
  }

  global.Activity = { render, TYPE_LABELS, h };
  global.Widgets = WIDGETS;
})(window);

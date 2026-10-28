/* Headless simulácia celého herného cyklu s mock DOM.
   Overuje, že engine (hra.js) nezhavaruje a že výsledky dávajú zmysel
   vo všetkých troch režimoch. Spustenie:  node sim.js   */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

/* ---- minimalistický mock DOM ---- */
function makeEl(id) {
  const el = {
    id, _children: [], style: {}, _text: "", _html: "", value: "",
    className: "", onclick: null, dataset: {},
    classList: { _s: new Set(),
      add(c){this._s.add(c);}, remove(c){this._s.delete(c);}, contains(c){return this._s.has(c);} },
    appendChild(c){ this._children.push(c); return c; },
    get children(){ return this._children; },
    set textContent(v){ this._text = v; }, get textContent(){ return this._text; },
    set innerHTML(v){ this._html = v; if(v==="") this._children = []; }, get innerHTML(){ return this._html; },
    select(){}, focus(){},
    getContext(){ return new Proxy({}, { get(){ return ()=>{}; } }); },
    addEventListener(){}, querySelector(){ return null; },
    width: 520, height: 380,
  };
  return el;
}
const els = {};
const gEl = (id) => (els[id] = els[id] || makeEl(id));
let chosenMode = "adaptivny";
const screens = ["screen-start","screen-game","screen-results"].map(makeEl);
const screenById = Object.fromEntries(screens.map(s=>[s.id,s]));

const document = {
  getElementById: (id) => screenById[id] || gEl(id),
  createElement: (t) => makeEl("_"+t+Math.random()),
  querySelector: (sel) => {
    if (sel.includes("checked")) return { value: chosenMode };
    return makeEl("q");
  },
  querySelectorAll: (sel) => sel === ".screen" ? screens : [],
  execCommand(){},
};
const window = {
  addEventListener(){}, DIMENZIE:null, BANKA:null,
};
const performance = { now: () => Date.now() };
const localStorage = { _d:{}, setItem(k,v){this._d[k]=v;}, getItem(k){return this._d[k];} };
const Blob = function(){}; const URL = { createObjectURL(){return "blob:x";} };

const ctx = vm.createContext({ document, window, performance, localStorage, Blob, URL,
  console, Math, Date, JSON, Array, Object, Number, String, Boolean, setTimeout, performance });

/* ---- načítaj banka.js + hra.js do spoločného kontextu ---- */
vm.runInContext(fs.readFileSync(path.join(__dirname,"banka.js"),"utf8"), ctx);
ctx.DIMENZIE = window.DIMENZIE; ctx.BANKA = window.BANKA;
vm.runInContext(fs.readFileSync(path.join(__dirname,"hra.js"),"utf8"), ctx);

/* ---- simuluj jedno sedenie v danom režime a danej stratégii ---- */
function playSession(mode, strategy) {
  chosenMode = mode;
  gEl("studentId").value = "SIM-"+mode;
  ctx.startGame();
  let guard = 0;
  while (screenById["screen-game"].style.display !== "none" && guard < 100) {
    guard++;
    const opts = gEl("options")._children;
    if (opts.length === 0) break;
    let pick;
    if (strategy === "ideal") {
      // engine zamiešal poradie; "ideálny" hráč nevie skóre, ale my áno cez onclick closure?
      // jednoduchšie: klikni náhodne, ale s preferenciou — tu klikneme prvý (náhodné poradie => realistický priemer)
      pick = opts[Math.floor(Math.random()*opts.length)];
    } else {
      pick = opts[Math.floor(Math.random()*opts.length)];
    }
    pick.onclick();                 // zaznamená odpoveď + zobrazí feedback
    ctx.nextItem();                 // ďalší uzol alebo finish()
  }
  // ak skončila hra, výsledky sú v state
  const res = ctx.computeResults ? ctx.computeResults() : null;
  return res;
}

let problems = 0;
for (const mode of ["adaptivny","genericky","kontrola"]) {
  try {
    const res = playSession(mode, "random");
    const ok = res && res.nItems >= 1 && res.overallPct >= 0 && res.overallPct <= 100
      && res.dimPct && typeof res.offloadingIdx === "number";
    console.log(`${ok?"✓":"✗"} režim ${mode}: ${res.nItems} uzlov, skóre ${res.overallPct}%, offloading ${res.offloadingIdx}%`);
    if (!ok) problems++;
    // over, že sa dosiahla obrazovka výsledkov
    if (screenById["screen-results"].style.display !== "block") { console.log("   ✗ nezobrazila sa obrazovka výsledkov"); problems++; }
  } catch (e) {
    console.log(`✗ režim ${mode} ZHAVAROVAL: ${e.message}`);
    problems++;
  }
}
console.log(`\n${problems===0 ? "✅ ENGINE BEŽÍ VO VŠETKÝCH REŽIMOCH" : "❌ PROBLÉMY: "+problems}`);
process.exit(problems===0?0:1);

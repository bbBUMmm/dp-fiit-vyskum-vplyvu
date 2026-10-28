/* Rýchly test integrity banky úloh + simulácia skórovania (Node, bez prehliadača).
   Spustenie:  node test.js   */
const fs = require("fs");
const path = require("path");

// načítaj banka.js do "window"
const window = {};
const code = fs.readFileSync(path.join(__dirname, "banka.js"), "utf8");
new Function("window", code)(window);
const { BANKA, DIMENZIE } = window;

let errors = 0;
const fail = (m) => { console.error("  ✗ " + m); errors++; };

console.log(`Položiek v banke: ${BANKA.length}`);
console.log(`Dimenzií: ${Object.keys(DIMENZIE).length}\n`);

// 1) integrita položiek
const ids = new Set();
for (const it of BANKA) {
  if (ids.has(it.id)) fail(`duplicitné id: ${it.id}`);
  ids.add(it.id);
  if (!DIMENZIE[it.dimension]) fail(`${it.id}: neznáma dimenzia ${it.dimension}`);
  if (![1,2,3].includes(it.difficulty)) fail(`${it.id}: zlá obtiažnosť`);
  if (!it.question) fail(`${it.id}: chýba otázka`);
  if (!Array.isArray(it.options) || it.options.length < 3) fail(`${it.id}: málo možností`);
  const hasCorrect = it.options.some(o => o.score === 2);
  if (!hasCorrect) fail(`${it.id}: žiadna možnosť so skóre 2`);
  const hasWrong = it.options.some(o => o.score === 0);
  if (!hasWrong) fail(`${it.id}: žiadna možnosť so skóre 0 (chýba pasca)`);
  for (const o of it.options) {
    if (![0,1,2].includes(o.score)) fail(`${it.id}: skóre mimo 0-2`);
    if (!o.text || !o.feedback) fail(`${it.id}: možnosť bez textu/feedbacku`);
  }
}

// 2) pokrytie dimenzií
const cov = {};
for (const it of BANKA) cov[it.dimension] = (cov[it.dimension]||0)+1;
console.log("Pokrytie dimenzií:");
for (const k of Object.keys(DIMENZIE)) {
  const n = cov[k]||0;
  console.log(`  ${n>0?"✓":"✗"} ${k}: ${n} položiek`);
  if (n === 0) fail(`dimenzia ${k} nemá žiadnu položku`);
}

// 3) vyváženosť pasce (aiCorrect)
const evalItems = BANKA.filter(it => it.aiSays);
const aiWrong = evalItems.filter(it => it.aiCorrect === false).length;
const aiRight = evalItems.filter(it => it.aiCorrect === true).length;
console.log(`\nAI vstup: ${evalItems.length} položiek (správna AI: ${aiRight}, nesprávna AI: ${aiWrong})`);
if (aiWrong === 0) fail("žiadna 'pasca' — AI sa nikdy nemýli");

// 4) simulácia skórovania: 'ideálny' žiak (vždy max) vs 'offloader' (vždy reliance)
function simulate(strategy) {
  const responses = [];
  for (const it of BANKA) {
    let opt;
    if (strategy === "ideal") opt = it.options.reduce((a,b)=>b.score>a.score?b:a);
    else { // offloader: preferuj reliance, inak najnižšie skóre
      opt = it.options.find(o=>o.reliance) || it.options.reduce((a,b)=>b.score<a.score?b:a);
    }
    responses.push({dimension:it.dimension, score:opt.score, reliance:!!opt.reliance, aiCorrect:it.aiCorrect});
  }
  const total = responses.reduce((s,r)=>s+r.score,0);
  const max = responses.length*2;
  const reliance = responses.filter(r=>r.reliance).length;
  return { pct: Math.round(total/max*100), offload: Math.round(reliance/responses.length*100) };
}
const ideal = simulate("ideal");
const offl = simulate("offloader");
console.log(`\nSimulácia — ideálny žiak: ${ideal.pct}% skóre, ${ideal.offload}% offloading`);
console.log(`Simulácia — offloader:    ${offl.pct}% skóre, ${offl.offload}% offloading`);
if (ideal.pct < 90) fail("ideálny žiak nedosiahol ~100% (chyba v skórovaní)");
if (offl.pct > 40) fail("offloader má privysoké skóre (pasce nefungujú)");
if (offl.offload <= ideal.offload) fail("offloading index nerozlišuje stratégie");

console.log(`\n${errors===0 ? "✅ VŠETKY TESTY PREŠLI" : "❌ CHÝB: "+errors}`);
process.exit(errors===0?0:1);

# Otázka 2 — Na ktoré slovenské školy aplikovať výskum

**DP:** Výskum vplyvu generických a adaptívnych nástrojov UI v školskom prostredí · FIIT STU

---

## 0. Zhrnutie na jednu obrazovku (TL;DR)

- **Pracujeme so stredoškolákmi (15–19 r.), nie s VŠ** — to mení dizajn (žiadny krížový dizajn ako Kestin, treba súhlas zákonných zástupcov pre maloletých).
- Slovensko má **233 gymnázií** a **437 SOŠ**; ~33 % stredoškolákov je na gymnáziu, ~63 % na SOŠ.
- **Najľahšie interpretovateľná vzorka = gymnázium, 2.–3. ročník, predmet matematika/informatika.** Dôvod: homogénna, akademicky orientovaná populácia, existujúce štandardizované testy, najnižší šum.
- **Najsilnejší vedecký dizajn = kontrast „gymnázium vs technická SOŠ“** — ukáže, či vplyv AI závisí od typu školy (originálne, ale náročnejšie).
- **3 varianty výberu** nižšie; **odporúčam Variant A (gymnázium-fokus) ako jadro + 1 technická SOŠ ako kontrastná vzorka** (hybrid, ktorý dáva čistotu aj originalitu).

---

## 1. Mapa slovenského stredného školstva (fakty pre obhajobu)

| Typ školy | Počet | Vek/ročníky | Zameranie | Maturita |
|---|---|---|---|---|
| **Gymnázium** | **233** (144 štátnych, 38 súkr., 51 cirk.) | 15–19 (4-roč.) alebo 10–19 (8-roč.) | všeobecné, príprava na VŠ | áno |
| **SOŠ** (stredná odborná) | **437** (335 štát., 83 súkr., 19 cirk.) | 15–19 (4-roč.) | odborné (technika, ekonomika, zdravotníctvo, umenie…) | áno (4-roč. odbory) |
| Konzervatóriá, športové gym. | málo | rôzne | špecializované | áno |

- **Podiel žiakov:** ~33 % gymnáziá, ~63 % SOŠ. Teda **väčšina slovenských stredoškolákov je na SOŠ** — to je dôležité pre reprezentatívnosť a pre vetu do práce „SOŠ tvoria väčšinu, no vo výskume AI sú podreprezentované“.
- **Vek a súhlas:** žiaci 1.–3. ročníka sú **maloletí** → nutný **informovaný súhlas zákonného zástupcu** + súhlas žiaka. 4. ročník/oktáva často 18+ → jednoduchšie. **Toto priamo ovplyvňuje výber ročníka.**
- **Kde sa AI reálne používa:** prieskumy (College Board, Pew, RAND 2025/26) — žiaci AI používajú najviac na **vysvetlenie zadaní (38 %), brainstorming (35 %), vyhľadávanie faktov (33 %), písanie/úpravu textu (33 %)**; matematiku rieši cez AI ~29 %. Teda **humanitné/písomné úlohy a matematika** sú prirodzené domény.

---

## 2. Aké kritériá rozhodujú o „dobrej“ škole pre tento výskum

Toto je analytické jadro — výber školy nie je náhodný, ale optimalizácia 6 kritérií:

1. **Homogenita vzorky** — čím podobnejší žiaci, tým menší šum, tým ľahšia interpretácia. (Gymnázium > SOŠ > zmiešané.)
2. **Existencia štandardizovaného testu pre predmet** — bez neho musíš tvoriť a validovať vlastný (riziko). Matematika/fyzika/informatika majú medzinárodné concept inventories.
3. **Digitálna a AI vybavenosť** — škola musí umožniť nainštalovať tvoj nástroj/proxy (alebo aspoň spustiť hru v prehliadači). IT-orientované školy = menej technických prekážok.
4. **Ochota vedenia a učiteľa** — bez „šampióna“ na škole sa experiment nezrealizuje. Toto býva *limitujúci* faktor, nie štatistika.
5. **Veková zrelosť a súhlasy** — vyššie ročníky = jednoduchšia etika, lepšie self-reporty.
6. **Variabilita, ak chceš porovnávať** — ak je cieľom porovnať *typy* škôl, potrebuješ aspoň 2 kontrastné profily.

> **Napätie medzi kritériami:** 1 (homogenita) a 6 (variabilita) idú proti sebe. Buď maximalizuješ čistotu (jeden typ školy), alebo maximalizuješ zovšeobecniteľnosť (viac typov). Práve preto sú nižšie 3 varianty — každý rieši toto napätie inak.

---

## 3. Tri varianty výberu škôl

### VARIANT A — „Gymnaziálny fokus“ (maximálna čistota)
**Vzorka:** 2–3 gymnáziá, 2.–3. ročník, predmet matematika alebo informatika. ~3 triedy → 3 experimentálne skupiny (adaptívny / generický / kontrola), ~60–90 žiakov.

- **Plusy:** najhomogénnejšia populácia → najmenší šum → najľahšia interpretácia. Žiaci sú zvyknutí na testovanie, lepšie self-reporty, vyššia pravdepodobnosť, že majú skúsenosť s AI. Matematika/informatika má hotové štandardizované testy. Najľahšia obhajoba pred komisiou.
- **Mínusy:** **slabá zovšeobecniteľnosť** — výsledky platia pre akademickú elitu, nie pre „priemerného slovenského stredoškoláka“ (ktorý je na SOŠ). Riziko stropového efektu (gymnazisti sú dobrí, málo priestoru na zlepšenie).

### VARIANT B — „Reprezentatívny prierez“ (maximálna zovšeobecniteľnosť)
**Vzorka:** mix gymnázium + SOŠ (technická aj netechnická) + rôzne kraje, stratifikované podľa typu školy a regiónu. Veľká vzorka (200+ žiakov).

- **Plusy:** výsledky platia pre celé Slovensko, silná externá validita, napĺňa „slovenská medzera v dátach“.
- **Mínusy:** **obrovský šum** (rôzne školy, učitelia, predmety, vybavenie) → potrebuješ veľké N a sofistikovanú štatistiku (viacúrovňové modely). Pre jedného diplomanta logisticky **takmer nereálne** za jeden semester. Vysoké riziko, že sa nepodarí získať dosť škôl.

### VARIANT C — „Kontrastný dizajn: gymnázium vs technická SOŠ“ ⭐ (ODPORÚČANÝ HYBRID)
**Vzorka:** **1–2 gymnáziá (jadro) + 1 technická SOŠ (kontrast)**, rovnaký ročník (2.–3.), rovnaká/ekvivalentná doména (napr. matematika/logika alebo informatika, ktorú majú oba typy). V každej škole 3-skupinový dizajn. Cieľ ~60 žiakov na typ školy.

- **Plusy:** dostaneš **čistotu Variantu A** (gymnázium ako dobre interpretovateľné jadro) **a navyše jednu originálnu výskumnú otázku** — *„líši sa vplyv AI podľa typu školy?“* — ktorú žiadna SOTA štúdia nerieši. Technická SOŠ (napr. SPŠ elektrotechnická, IT odbory) má **vysokú AI/digitálnu vybavenosť** → menej technických prekážok pri nasadení nástroja. Stále zvládnuteľné jedným diplomantom.
- **Mínusy:** treba zladiť doménu naprieč dvoma typmi škôl (mitigácia: vyber tému, ktorú majú obe — logika/matematika/základy programovania). O niečo viac koordinácie.

---

## 4. Výber a hĺbkový „čo ak“ rozbor — VARIANT C

Vyberám **Variant C**. Logika v jednej vete: gymnaziálne jadro mi dá interpretovateľnosť, ktorú komisia chce, a jedna technická SOŠ mi dá originálny kontrast, ktorý zvýši hodnotu práce — bez logistického šialenstva Variantu B.

### Reťaz „čo ak“ (s odhadom istoty)

**ČO AK** ako jadro vyberieme **gymnázium, 2.–3. ročník, predmet matematika/informatika**
→ **DOSTANEME** homogénnu vzorku s existujúcimi testami a najnižším šumom. **Istota ~95 %**, že interpretácia bude čistá, lebo eliminujeme medzipredmetové a medziškolské rozdiely.
→ **PREČO nie 1. ročník:** ešte sa adaptujú na SŠ, vyššia fluktuácia. **PREČO nie 4. ročník/maturanti:** sústredia sa na maturitu/prijímačky, nízka ochota, časté absencie. **2.–3. ročník je „sweet spot“.** Istota ~90 %.

**ČO AK** pridáme **jednu technickú SOŠ** (SPŠ — elektro/IT/strojárstvo) s rovnakým ročníkom a ekvivalentnou doménou
→ **DOSTANEME** kontrastnú skupinu, ktorá má (a) vyššiu digitálnu zdatnosť → hladšie nasadenie nástroja, (b) odlišný profil vzťahu k AI. **Istota ~85 %**, že nameráme rozdiel medzi typmi škôl v *spôsobe* používania AI (nie nutne vo výsledkoch) — to je presne ten zaujímavý nález.
→ **HYPOTÉZA (čo asi vyjde):** gymnazisti budú AI používať viac na „pochopenie“, žiaci SOŠ viac na „rýchlu hotovú odpoveď“ → vyšší offloading na SOŠ. **Toto je testovateľná, publikovateľná hypotéza.** (Pozn.: nie je to istota, je to očakávanie — v práci formulovať ako hypotézu, nie ako fakt.)

**ČO AK** doménu zvolíme ako **„logika / základy programovania / matematika“ spoločnú obom typom škôl**
→ **DOSTANEME** porovnateľnosť naprieč školami (rovnaký test). **Istota ~90 %**, že takúto prienikovú doménu nájdeme — informatika/matematika je povinná na oboch.
→ **RIZIKO:** technická SOŠ môže mať z danej témy náskok → stropový efekt. **Mitigácia:** vyber tému, ktorú práve preberajú obe (konzultácia s učiteľmi), alebo „novú“ tému pre oboch (napr. konkrétny algoritmus, ktorý ešte nemali).

**ČO AK** zacielime na **2.–3. ročník (väčšinou maloletí)** a vyriešime súhlasy vopred
→ **DOSTANEME** ideálny vek, ale **musíme** mať informovaný súhlas rodičov. **Istota ~99 %**, že etická komisia FIIT to bude vyžadovať. **Mitigácia:** šablóny súhlasov pripraviť hneď (oddelene žiak/rodič), počítať s 3–4 týždňami na schválenie etiky — **toto začať najskôr** (pozri Dokument 5).

**ČO AK** cielime **~60 žiakov na typ školy (≈120 spolu)** rozdelených do 3 skupín
→ **DOSTANEME** dosť na detekciu stredných efektov. Power analýza (3 skupiny, stredný efekt, α=0,05, sila 0,8) → **min. 18/skupina = 54 spolu**; s rezervou na výpadky (+30 %) a na porovnanie typov škôl cielime vyššie. **Istota ~99 %** (matematika power analýzy je istá); reálne riziko je *nábor*, nie štatistika.

**ČO AK** sa technická SOŠ nepodarí získať (najpravdepodobnejší problém)
→ **FALLBACK na Variant A** (čisto gymnázium) — práca ostáva plne validná, len bez medziškolského kontrastu. **Vždy máme ústupovú cestu.** Preto je gymnázium *jadro* a SOŠ *bonus*, nie naopak.

### Aké konkrétne školy osloviť (typy, nie mená — mená doplníš podľa kontaktov školiteľa/STU)
- **Gymnáziá:** mestské gymnáziá s dobrou IT vybavenosťou; cez postavenie STU ako národného kompetenčného centra pre AI vo vzdelávaní (citované v tvojej SOTA) máš **silnú vyjednávaciu páku** — školy budú motivované spolupracovať s STU.
- **Technická SOŠ:** SPŠ elektrotechnická / informačných technológií (napr. typu SPŠE, SPŠ IT) — majú infraštruktúru aj žiakov zvyknutých na nástroje.
- **Páka:** rámcuj to ako „pilot Plánu zodpovedného využívania AI 2025–2027“ + „spolupráca s STU kompetenčným centrom“. To otvára dvere, ktoré by inak boli zavreté.

---

## 5. Čo povedať školiteľovi (zhrnutie)

> **„Jadrom vzorky bude gymnázium, 2.–3. ročník, predmet matematika/informatika — najhomogénnejšia a najľahšie interpretovateľná populácia s hotovými testami. K tomu pridám jednu technickú SOŠ ako kontrastnú vzorku, čím získam originálnu výskumnú otázku ‚líši sa vplyv AI podľa typu školy?‘, ktorú zatiaľ nikto neskúmal. Cielim ~60 žiakov na typ školy v 3-skupinovom dizajne. Ak sa SOŠ nepodarí získať, mám čistý fallback na samotné gymnázium. Postavenie STU ako kompetenčného centra použijem ako páku pri získavaní škôl, a etické súhlasy rodičov začnem riešiť okamžite, lebo žiaci sú maloletí.“**

---

## 6. Otvorené body na rozhodnutie
1. **Región** — Bratislava (blízko STU, ľahšia koordinácia) vs. iný kraj (lepšia reprezentatívnosť). Odporúčam BA kvôli logistike.
2. **Predmet/doména** — finálne rozhodnutie po konzultácii s učiteľmi oboch škôl (Dokument 1, bod 1).
3. **Nasadenie nástroja vs. hra v prehliadači** — na SOŠ ľahšie nainštalovať proxy; na gymnáziu možno radšej hra v prehliadači (Dokument 4) bez inštalácie. Toto rozhodne IT realita školy.

---

## Zdroje
- Typy a počty SŠ na SK: [CVTI SR — prehľad SŠ](https://www.cvtisr.sk/cvti-sr-vedecka-kniznica/informacie-o-skolstve/publikacie-casopisy.../zistovanie-kvalifikovanosti/prehlad-strednych-skol.html?page_id=9574), [CVTI štatistická ročenka SOŠ](https://www.cvtisr.sk/cvti-sr-vedecka-kniznica/informacie-o-skolstve/statistiky/statisticka-rocenka-publikacia/statisticka-rocenka-stredne-odborne-skoly.html), [Eurydice — organizácia SK školstva](https://eurydice.eacea.ec.europa.eu/eurypedia/slovakia/organisation)
- Gymnázium vs SOŠ (rozdiely, ročníky, vek): [SAIA — vzdelávací systém SK](https://spehp.saia.sk/sk/main/vzdelavacie-systemy-krajin/vzdelavaci-system-na-slovensku/), [ŽSK školský systém](http://www.zilinskazupa.sk/sk/samosprava/urad-zsk/odbor-skolstva-sportu/kompetencie-hlavne-cinnosti-odboru/skolsky-system-slovenskej-republike.html)
- Počty (233 gymnázií, 437 SOŠ): [STUDYIN prehľad SŠ](https://studyin.sk/slovensko/kompletny-prehlad-strednych-skol-na-slovensku/), [INEKO hodnotenie škôl](https://skoly.ineko.sk/)
- Ktoré predmety/úlohy žiaci riešia cez AI: [College Board](https://newsroom.collegeboard.org/new-research-majority-high-school-students-use-generative-ai-schoolwork), [Pew Research](https://www.pewresearch.org/short-reads/2025/01/15/about-a-quarter-of-us-teens-have-used-chatgpt-for-schoolwork-double-the-share-in-2023/), [RAND 2026](https://www.rand.org/news/press/2026/03/student-use-of-ai-for-homework-rises-as-concerns-grow.html)

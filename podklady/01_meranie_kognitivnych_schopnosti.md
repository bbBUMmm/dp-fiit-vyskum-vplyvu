# Otázka 1 — Ako konkrétne merať kognitívne schopnosti žiakov

**Diplomová práca:** Výskum vplyvu generických a adaptívnych nástrojov UI v školskom prostredí
**Školiteľ:** Ing. Miroslav Bahleda, PhD. · FIIT STU
**Podklad pre stretnutie** · spracované v noci, určené na rannú prezentáciu

---

## 0. Zhrnutie na jednu obrazovku (TL;DR)

- **Nemeriame „IQ“.** Klasický IQ test (Wechsler, IST) je pre náš výskum nesprávny nástroj — meria stabilnú, ťažko ovplyvniteľnú vlastnosť, ktorá sa za jednu intervenciu s AI nezmení. Mýlili by sme si **predpoklad** (čo žiak má) so **stavom** (čo žiak práve robí/dokáže po intervencii).
- **Meriame v 3 vrstvách:** (A) **vedomostný zisk** v konkrétnej téme, (B) **prenositeľné myslenie** (kritické myslenie + metakognícia), (C) **vzťah k AI** (kognitívne offloadenie, dôvera, AI gramotnosť).
- **Odporúčaný nástroj na kritické myslenie:** **nekupovať** drahý HCTA od Schuhfried (komerčný, drahý, anglický). Namiesto toho **vlastná krátka batéria úloh** validovaná na pilote + voľne dostupné škály (Gerlichove offloading položky, AI literacy 12 položiek). Halpernov model (5 dimenzií) použijeme ako **teoretickú kostru**, nie ako kúpený produkt.
- **3 varianty** meracej batérie sú nižšie; **odporúčam Variant C (hybrid)** a rozoberám ho do hĺbky metódou „čo ak“.

---

## 1. Čo vlastne chceme zmerať? (toto je jadro problému)

Pred výberom konkrétneho dotazníka treba odpovedať na otázku, ktorá v zadaní DP zaznieva implicitne: **„vplyv AI na schopnosti žiaka“ — na ktoré schopnosti?** Bez tohto rozhodnutia sa nedá vybrať nástroj. Rozlišujeme tri vrstvy, pretože každú meria iný typ nástroja a každá odpovedá na inú výskumnú otázku.

| Vrstva | Čo meria | Príklad otázky výskumu | Typ nástroja |
|---|---|---|---|
| **A. Vedomosti (doménové)** | Koľko sa žiak naučil o konkrétnej téme | „Naučí sa žiak kvadratické rovnice lepšie s AI tútorom alebo bez?“ | Doménový test / *concept inventory* |
| **B. Prenositeľné myslenie** | Kritické myslenie, metakognícia — *ako* žiak premýšľa, nezávisle od témy | „Oslabuje časté používanie AI schopnosť žiaka kriticky hodnotiť tvrdenia?“ | HCTA, Watson-Glaser, MAI |
| **C. Vzťah k AI** | Ako veľmi sa žiak na AI spolieha, či jej dôveruje, či jej rozumie | „Existuje skupina žiakov, ktorá AI slepo dôveruje a má slabšie myslenie?“ | Offloading škála, AI literacy, SAID |

> **Kľúčový rozdiel oproti tvojmu doterajšiemu mysleniu (IQ/psychometria):** IQ a všeobecné mentálne schopnosti (odkaz zssambra.sk — Wechsler, IST, Army beta) patria do kategórie **stabilných čŕt (traits)**. Tie sa za 60–90 minút intervencie s AI **nezmenia** — to je psychometricky overené. Ak by si pre-test/post-testom meral IQ, namáhavo by si dokázal len to, že IQ je stabilné. To nie je tvoj výskum. Tvoj výskum je o **stave a správaní (states/behaviour)** — a tie meriame vrstvami A, B, C. IQ test má v práci jediné legitímne miesto: ako **kontrolnú premennú** (covariate), aby sme vedeli, či skupiny neboli náhodou nerovnako „chytré“ už na začiatku.

---

## 2. Katalóg konkrétnych nástrojov (čo merajú, ako, koľko, za koľko)

### 2.A — Kritické myslenie

#### HCTA — Halpern Critical Thinking Assessment
- **Čo meria:** 5 dimenzií kritického myslenia — (1) verbálne uvažovanie, (2) analýza argumentov, (3) testovanie hypotéz, (4) pravdepodobnosť a neistota, (5) rozhodovanie a riešenie problémov.
- **Formát:** kombinácia otvorených (constructed-response) aj uzavretých (forced-choice) položiek — *jediný* test, ktorý meria aj rozpoznanie aj vybavenie. To je psychometricky jeho hlavná prednosť.
- **Rozsah/čas:** 25 scenárov, ~20 min (krátka forma) až 45–60 min (plná).
- **Dostupnosť/cena:** ⚠️ **komerčný produkt firmy Schuhfried (Vienna Test System), Rakúsko. Platený per-administration, anglicky/nemecky, žiadna oficiálna SK verzia.** Pre stovky žiakov by licencia bola finančne aj administratívne neúnosná. Toto je presne tá štúdia (Gerlich), ktorú citujeme — on si licenciu mohol dovoliť.
- **Očakávané výsledky:** skóre 0–~190 bodov, normované. V Gerlichovej štúdii silná **negatívna korelácia** s frekvenciou používania AI (r ≈ −0,68) a s mierou offloadingu.
- **Verdikt pre DP:** použiť ako **teoretickú kostru** (5 dimenzií), **nie kupovať**.

#### Watson-Glaser Critical Thinking Appraisal (WGCTA)
- **Čo meria:** 5 subškál — inferencia, rozpoznanie predpokladov, dedukcia, interpretácia, hodnotenie argumentov.
- **Formát:** uzavreté otázky (multiple-choice). Najstarší a najpoužívanejší CT test, používa sa pri nábore.
- **Dostupnosť/cena:** komerčný (Pearson TalentLens), platený, anglicky. Rovnaký problém ako HCTA.

#### CCTST — California Critical Thinking Skills Test
- **Čo meria:** analýzu, hodnotenie, inferenciu, deduktívne a induktívne uvažovanie. Má „sesterský“ dotazník dispozícií CCTDI (sklon ku kritickému mysleniu).
- **Dostupnosť:** komerčný (Insight Assessment), platený.

#### Cornell Critical Thinking Test (CCTT)
- **Čo meria:** indukcia, dedukcia, dôveryhodnosť, identifikácia predpokladov.
- **Dôležité pre nás:** **Level X je explicitne určený pre žiakov od 5. ročníka po strednú školu** — t. j. presne náš vek. Level Z je pre VŠ. Cornell je vekovo najvhodnejší zo „značkových“ testov.
- **Dostupnosť:** komerčný, ale lacnejší a dostupnejší než HCTA.

#### Ennis-Weir Critical Thinking Essay Test (EWCTET)
- **Čo meria:** schopnosť **posúdiť a napísať argument** — otvorený esejový test (40 min, žiak píše odpoveď na argumentačný list).
- **Dôležité pre nás:** toto je presne formát, ktorý **už používaš** (otvorené otázky). Má **rubriku** na skórovanie a medzihodnotiteľská zhoda 0,75–0,85. Ak chceš ostať pri otvorených otázkach, EWCTET je validovaný most medzi „otvorené“ a „dá sa to skórovať objektívne“.
- **Dostupnosť:** manuál Ennis & Weir (1985), lacný, voľnejšie dostupný.

#### CRT — Cognitive Reflection Test (Frederick)
- **Čo meria:** sklon potlačiť intuitívnu (nesprávnu) odpoveď a uvažovať reflektívne. **Len 3 (resp. 7 v rozšírenej verzii) otázok, ~5 min.**
- **Dôležité pre nás:** je **voľne dostupný, krátky, ľahko skórovateľný**, existujú lokalizácie. Ideálny ako rýchly „doplnok“ do batérie. Slávna otázka: *„Pálka a loptička stoja spolu 1,10 €. Pálka stojí o 1 € viac ako loptička. Koľko stojí loptička?“* (intuitívne 10 c, správne 5 c.) Priamo testuje, či žiak „naletí“ rýchlej odpovedi — analógia k slepému prebratiu odpovede od AI.

### 2.B — Metakognícia a sebaregulácia

#### MAI — Metacognitive Awareness Inventory (Schraw & Dennison, 1994)
- **Čo meria:** 52 položiek, 2 faktory: **Znalosť o poznávaní** (deklaratívna, procedurálna, podmienková — 17 položiek) a **Regulácia poznávania** (plánovanie, monitorovanie, manažment informácií, debugging, hodnotenie — 35 položiek).
- **Formát:** sebahodnotiace tvrdenia (súhlas/nesúhlas alebo Likert).
- **Dostupnosť/cena:** ✅ **VOĽNE dostupný v literatúre, validovaný, existujú adaptácie do mnohých jazykov** (portugalská, španielska, atď. — SK adaptáciu treba doložiť prekladom + pilotom).
- **Prečo je relevantný:** metakognícia = „premýšľanie o vlastnom premýšľaní“. Hypotéza celej tvojej práce (a Kosmynovej štúdie) je, že AI **vypína** metakognitívne monitorovanie — žiak nesleduje, či vlastne rozumie. MAI to meria priamo a zadarmo. Existuje aj 19-položková krátka verzia (MAI-R).

### 2.C — Vzťah k AI (toto je „srdce“ tvojej originality)

#### Gerlichova škála kognitívneho offloadingu
- **Čo meria:** mieru, do akej človek prenáša myslenie na nástroje. Položky typu: frekvencia používania vyhľadávača; „informácie nájdem rýchlejšie cez technológiu“; používanie telefónu na zapamätanie; „radšej vyhľadám než vyriešim sám“; závislosť od zariadení. Škála 1–6.
- **Dostupnosť:** ✅ položky **publikované v open-access článku** (Societies 2025) — môžeš ich prevziať a citovať. Presne ten nástroj, ktorý je v tvojej SOTA kapitole.

#### SAID — Scale of AI Dependence (akademické úlohy)
- **Čo meria:** 3 dimenzie — **„informačná exkluzivita s AI“** (spolieham sa len na AI), **„dôvera v AI“**, **„AI gramotnosť“**.
- **Dôležité pre nás:** ✅ **validovaný priamo na stredoškolákoch** (370 žiakov, 8 škôl, Peru, 2025). Vekovo presne sedí. Skvelý doplnok ku Gerlichovi.

#### AI Literacy Scale (Wang et al., 2022) a AILQ (Ng et al., 2024)
- **Čo meria:** Wang — **12 položiek, 4 dimenzie: povedomie, používanie, hodnotenie, etika.** Validované **na stredoškolákoch.** Ng — 32 položiek (afektívne, behaviorálne, kognitívne, etické učenie), tiež stredoškoláci (Hongkong).
- **Dostupnosť:** ✅ položky publikované. Krátky Wang (12 položiek) je ideálny do batérie.

#### Lee et al. — 6 aspektov kognitívneho úsilia (z tvojej SOTA)
- Nie je to „dotazník na kúpenie“, ale **6-položkový rámec** (identifikácia cieľa, formulácia dopytu, vyhodnotenie odpovede, integrácia, reflexia, transfer) hodnotený na 5-bodovej škále pri konkrétnej úlohe. Toto je most medzi self-reportom a reálnym správaním a **dá sa priamo zabudovať do tvojej hry/nástroja** (pozri Dokument 4).

### 2.D — Všeobecné rozumové schopnosti / IQ (kontrolná premenná, nie hlavná metrika)

#### Ravenove progresívne matice (SPM / APM / CPM)
- **Čo meria:** *fluidnú inteligenciu* — neverbálne logické uvažovanie, rozpoznávanie vzorov. Bez jazyka → bez kultúrneho/jazykového skreslenia.
- **Verzie:** SPM (štandardné, bežná populácia od 8 r.), **APM (pre pokročilých — autori odporúčajú práve na výber žiakov do prírodovedných a technických programov)**, CPM (farebné, deti/seniori).
- **Dostupnosť na SK:** ✅ **vydané Psychodiagnostikou (1991), Hogrefe-Testcentrum má české normy.** Existuje slovenská distribúcia (psychodiagnostika.sk). Pozor: predaj často viazaný na psychologické vzdelanie.
- **Úloha v DP:** **kontrolná premenná** (covariate). Krátky Raven (alebo jeho podmnožina) na začiatku zabezpečí, že vieš, či experimentálna a kontrolná skupina mali porovnateľnú fluidnú inteligenciu. Ak nie, použiješ ho v ANCOVA ako kovariát (pozri Dokument 3).

#### IST (Test štruktúry inteligencie), Wechsler (WISC-V/WAIS), Army Beta
- Komplexné batérie merajúce viac schopností (verbálne, numerické, figurálne, pamäť…). **Pre DP nadbytočné** — administratívne náročné (60–90 min len IQ), drahé, viazané na psychológa. Spomenúť v texte ako „zvažované a vyradené a prečo“ — to robí prácu metodologicky vyspelejšou.

---

## 3. Tri varianty meracej batérie

> Toto je formát, ktorý si žiadal: 3 varianty, z ktorých jeden vyberiem a rozoberiem do hĺbky.

### VARIANT A — „Doménový“ (čistý vedomostný zisk)
**Filozofia:** kopíruje Slijepcevica (Khanmigo vs Google) a princíp *concept inventory*. Vyberieš jednu tému (napr. kvadratické rovnice / fotosyntéza / cykly v programovaní), vytvoríš/adaptuješ štandardizovaný test s 15–25 uzavretými otázkami, kde nesprávne možnosti = typické miskoncepcie. Meriaš pre-test → intervencia s/bez AI → post-test.

- **Meria:** vrstvu A (vedomosti).
- **Plusy:** najľahšie obhájiteľné pred komisiou, najľahšia interpretácia (normalizovaný zisk g, Cohenovo d), priamo porovnateľné so Slijepcevicom, učitelia to chápu okamžite.
- **Mínusy:** nemeria *prenositeľné* myslenie ani vzťah k AI. Riziko, že nameriaš len „AI dá rýchlo odpoveď, takže post-test je lepší“ — bez hĺbky. Nezachytáva tvoju originálnu tému (kognitívny dlh).

### VARIANT B — „Psychometrický transfer“ (kritické myslenie + metakognícia)
**Filozofia:** kopíruje Gerlicha. Pre-test = HCTA-typ batéria + MAI. Intervencia (žiaci dlhšie obdobie používajú/nepoužívajú AI). Post-test = ekvivalentná CT batéria + MAI. Hľadáš zmenu v *spôsobe myslenia*.

- **Meria:** vrstvu B (prenositeľné myslenie).
- **Plusy:** meria presne to, čoho sa spoločnosť bojí (úpadok kritického myslenia). Vysoká vedecká hodnota, priamo nadväzuje na Gerlicha a Kosmynu.
- **Mínusy:** kritické myslenie sa **mení pomaly** — jedna lekcia ho neposunie. Vyžaduje **longitudinálny** dizajn (týždne až mesiace), inak nameriaš nulu. HCTA je drahý/anglický → treba vlastnú validovanú batériu (riziko nižšej validity). Náročné na obhajobu „toto naozaj meria kritické myslenie“.

### VARIANT C — „Hybridná batéria“ ⭐ (ODPORÚČANÝ)
**Filozofia:** kombinuje všetky tri vrstvy v zvládnuteľnom čase (~40–45 min na sedenie) a **prepája self-report s reálnym správaním** zachyteným tvojím nástrojom/hrou. Toto je presne tá „medzera“, ktorú v SOTA identifikuješ (self-report dominuje, chýba behaviorálne meranie).

**Zloženie pre-testu (≈40 min):**
1. **Krátky doménový test** — 12–15 uzavretých otázok z jednej témy (15 min) → vrstva A
2. **Krátka CT batéria** — 8–10 úloh inšpirovaných Halpernovými 5 dimenziami + 3 CRT otázky (12 min) → vrstva B
3. **AI-vzťahové škály** — Gerlich offloading (skrátený) + Wang AI literacy 12 položiek + SAID „dôvera v AI“ (10 min) → vrstva C
4. *(voliteľne, raz)* **6–8 položiek Raven** ako kontrola fluidnej inteligencie (5 min)

**Intervencia:** 3-skupinový dizajn (adaptívny nástroj / generický ChatGPT / kontrola bez AI) — žiaci riešia úlohy, **tvoj nástroj loguje reálne prompty a správanie** (čas, úpravy, počet dopytov).

**Post-test (≈30 min):** ekvivalentný doménový test + ekvivalentná CT batéria + krátky dotazník vnímania.

- **Meria:** A + B + C **a navyše** behaviorálnu vrstvu (logy) → 4 zdroje dát, ktoré sa dajú **triangulovať**.
- **Plusy:** najvyššia vedecká hodnota, priamo napĺňa všetky 3 medzery z tvojej SOTA, flexibilné (každú vrstvu vieš analyzovať aj samostatne), prepája kvantitatívne self-reporty s objektívnym správaním.
- **Mínusy:** najnáročnejšie na prípravu a pilotovanie, dlhší čas v triede (treba súhlas školy), viac premenných = náročnejšia analýza (riešim v Dokumente 3).

---

## 4. Výber a hĺbkový rozbor metódou „čo ak“ — VARIANT C

Vyberám **Variant C (hybrid)**. Dôvod v jednej vete: jediný napĺňa zadanie DP („vplyv na schopnosti“ = viac než vedomosti) **a zároveň** využíva tvoj unikátny technický prínos (logovanie reálnych interakcií), ktorý žiadna z 5 SOTA štúdií nemá v plnej forme. Teraz ho rozoberiem ako reťaz rozhodnutí — *čo ak spravíme X → dostaneme Y*.

### Reťaz „čo ak“ (s odhadom istoty)

**ČO AK** vyberieme jednu úzku doménu s existujúcim *concept inventory* (napr. mechanika → Force Concept Inventory, alebo astronómia → LPCI ako Slijepcevic) **namiesto vlastného doménového testu**
→ **DOSTANEME** okamžitú validitu a medzinárodnú porovnateľnosť bez nutnosti dokazovať, že náš test niečo meria. **Istota ~95 %**, že to obháji komisia, lebo presne to urobil Slijepcevic a prešlo to recenziou.
→ **RIZIKO:** FCI je o fyzike, ktorú na SOŠ nemusia mať rovnako. **Mitigácia:** vybrať doménu podľa typu školy (pozri Dokument 2) — na gymnáziu fyzika/matematika, na SOŠ odborný predmet.

**ČO AK** namiesto kúpy HCTA postavíme **vlastnú 8–10-úlohovú CT batériu** mapovanú 1:1 na Halpernových 5 dimenzií a **pilotne ju zvalidujeme** na ~30 žiakoch (Cronbach α, položková analýza)
→ **DOSTANEME** legálne použiteľný, slovenský, bezplatný nástroj, ktorý vieme citovať ako „inšpirovaný HCTA“. **Istota ~80 %**, že dosiahneme prijateľnú reliabilitu (α > 0,7), ak položky dobre napíšeme — toto je hlavné metodologické riziko a treba naň čas.
→ **POISTKA:** ak vlastná batéria zlyhá na pilote, **fallback je Cornell Level X** (vekovo vhodný, lacnejší než HCTA) alebo čisto Ennis-Weir esej + CRT. Vždy máme náhradný plán.

**ČO AK** doplníme self-report (Gerlich offloading, SAID, AI literacy) o **behaviorálne ukazovatele z logov** (čas čítania odpovede, miera úprav výstupu, počet doplňujúcich otázok, čas „premýšľania“ pred promptom)
→ **DOSTANEME** to, čo Kosmyna dosiahla EEG-čkom, ale **lacno a škálovateľne** — objektívny proxy kognitívneho zapojenia. **Istota ~90 %**, že korelácia self-report ↔ správanie bude detegovateľná pri N ≥ 60/skupina; **istota ~99 %**, že tieto dáta vieme zozbierať technicky (nástroj už prompty zachytáva).
→ **NÁSLEDOK:** ak žiaci s vysokým „trust in AI“ (SAID) majú zároveň krátky čas čítania a málo úprav (logy) a nižší CT zisk (test), máme **trianguláciou potvrdený** mechanizmus offloadingu — to je publikovateľný výsledok.

**ČO AK** pridáme 6–8 Ravenových položiek ako kontrolnú premennú
→ **DOSTANEME** schopnosť v analýze (ANCOVA) odfiltrovať, že rozdiel medzi skupinami nie je len tým, že jedna bola „chytrejšia“. **Istota ~99 %**, že recenzent/oponent sa spýta „kontrolovali ste vstupné schopnosti?“ — a my budeme mať odpoveď.

**ČO AK** sa rozhodneme **nemerať plné IQ ani Wechslera**
→ **DOSTANEME** úsporu 60+ min na žiaka a vyhneme sa nutnosti prizvať klinického psychológa a riešiť licencie. **Istota ~99 %**, že to bola správna voľba — full IQ jednoducho neodpovedá na žiadnu z našich výskumných otázok.

### Čo z Variantu C konkrétne „vypadne“ ako výsledok (očakávané dáta)

Pri Variante C budeš mať pre každého žiaka **vektor**:
```
žiak_id, skupina(adapt/gen/kontrola),
  domena_pre, domena_post, g_zisk,
  CT_pre, CT_post, CRT,
  MAI, offloading, AI_literacy, trust_AI,
  raven_kontrola,
  [LOGY] pocet_promptov, priem_dlzka_promptu, cas_citania_s,
         miera_uprav_%, pocet_doplnujucich_otazok
```
Z tohto vektora vieš robiť všetko z Dokumentu 3: porovnanie skupín (ANCOVA), koreláciu trust↔CT (replikácia Lee/Gerlich), zhlukovanie žiakov do profilov (replikácia Tomczyka), mediačnú analýzu offloadingu (replikácia Gerlicha).

---

## 5. Konkrétne finálne odporúčanie (čo povedať školiteľovi)

> **„Navrhujem hybridnú meraciu batériu o 4 vrstvách. Vedomostný zisk meriam adaptovaným concept inventory; kritické myslenie vlastnou 8–10-úlohovou batériou mapovanou na Halpernových 5 dimenzií (HCTA nekupujeme — je komerčný a anglický, použijeme ho ako teoretický rámec a pilotne zvalidujeme vlastné položky); vzťah k AI tromi voľne dostupnými škálami (Gerlich, SAID, Wang AI literacy); a unikátne to dopĺňam behaviorálnymi logmi z vlastného nástroja, čím nahrádzam Kosmynovo EEG lacnou, škálovateľnou alternatívou. Raven použijem len ako kontrolnú premennú, plné IQ nemeriam, lebo neodpovedá na výskumné otázky.“**

### Tabuľka: finálny výber nástrojov

| Vrstva | Nástroj | Položiek / čas | Dostupnosť | Náklad |
|---|---|---|---|---|
| A vedomosti | Adaptovaný concept inventory (FCI/LPCI/vlastný) | 12–15 / 15 min | voľné / vlastné | 0 € |
| B myslenie | Vlastná CT batéria (5 Halpern dimenzií) + CRT | 8–10 + 3 / 15 min | vlastné, pilot | 0 € |
| B metakognícia | MAI (krátka forma MAI-R) | 19 / 7 min | voľné, preklad | 0 € |
| C vzťah k AI | Gerlich offloading + SAID trust + Wang AI literacy | ~30 / 10 min | open-access | 0 € |
| D kontrola | Raven SPM/APM výber | 6–8 / 5 min | Psychodiagnostika SK | licencia* |
| behaviorálne | Logy z vlastného nástroja/hry | priebežne | vlastné | 0 € |

\* Raven je jediná položka s licenciou; ak by bol problém, nahradíš ho voľne dostupným *matrix reasoning* itemsetom (napr. ICAR — International Cognitive Ability Resource, ktorý je open-source). **To je dôležitá poznámka — ICAR rieši aj posledný licenčný problém.**

---

## 6. Otvorené body na rozhodnutie so školiteľom
1. **Doména pre vedomostný test** — viazať na typ školy (Dokument 2). Treba 1 rozhodnutie: matematika, fyzika, alebo odborný predmet?
2. **Longitudinálne vs. jednorazovo** — vrstva B (myslenie) potrebuje čas; vrstva A (vedomosti) stačí jednorazovo. Toto určuje celý harmonogram (Dokument 5).
3. **Validácia vlastnej CT batérie** — naplánovať pilot (~30 žiakov) pred ostrým zberom. **Toto je najväčšie metodologické riziko, treba mu vyhradiť 2–3 týždne.**

---

## Zdroje
- Halpern CTA — psychometria a dimenzie: [ScienceDirect cross-national](https://www.sciencedirect.com/science/article/abs/pii/S1871187112000247), [Wiley validačná štúdia CCTT vs HCTA](https://onlinelibrary.wiley.com/doi/10.1155/2013/198920), [APA PsycNet HCTA](https://psycnet.apa.org/doiLanding?doi=10.1037%2Ft10940-000)
- HCTA komerčná dostupnosť (Schuhfried): [Buros/UNL Marketplace](https://marketplace.unl.edu/buros/halpern-critical-thinking-assessment.html), [kritika dostupnosti](https://www.researchgate.net/publication/269738509)
- Watson-Glaser / CCTST / Cornell porovnanie: [ScienceDirect WGCTA štruktúra](https://www.sciencedirect.com/science/article/abs/pii/S1871187107000430), [EJ1109287 prehľad](https://files.eric.ed.gov/fulltext/EJ1109287.pdf)
- Ennis-Weir esejový test: [test review](https://scispace.com/papers/the-ennis-weir-critical-thinking-essay-test-an-instrument-qrqngmjp2n), [CriticalThinking.NET](https://criticalthinking.net/test/)
- MAI (Schraw & Dennison): [Lafayette PDF nástroja](https://advising.lafayette.edu/wp-content/uploads/sites/247/2021/10/metacognitive_awareness_inventory.pdf), [faktorová štruktúra](https://www.researchgate.net/publication/318669525)
- Gerlich offloading položky: [phys.org zhrnutie](https://phys.org/news/2025-01-ai-linked-eroding-critical-skills.html), [Substack rozbor](https://michellemillerphd.substack.com/p/cognitive-offloading-cognitive-abilities)
- SAID (stredoškoláci): [OJCMT článok](https://www.ojcmt.net/article/artificial-intelligence-dependence-in-academic-tasks-design-and-validation-of-the-said-questionnaire-17303), [PDF](https://www.ojcmt.net/download/artificial-intelligence-dependence-in-academic-tasks-design-and-validation-of-the-said-questionnaire-17303.pdf)
- AI literacy (Wang 12 položiek, Ng AILQ): [BJET Ng 2024](https://bera-journals.onlinelibrary.wiley.com/doi/10.1111/bjet.13411), [MAILS](https://www.sciencedirect.com/science/article/pii/S2949882123000142)
- Ravenove matice SK: [psychodiagnostika.sk APM](https://psychodiagnostika.sk/produkt/t-224-ravenove-progresivne-matice-pre-pokrocilych/), [Meranie inteligencie (RG)](https://www.researchgate.net/publication/374477680_Meranie_inteligencie)
- Concept inventories: [Wikipedia Concept inventory](https://en.wikipedia.org/wiki/Concept_inventory), [PhysPort best practices](https://www.physport.org/expert/AdministeringConceptInventories/)
- CRT — Cognitive Reflection Test: [HKU critical thinking tests](https://philosophy.hku.hk/think/critical/tests.php)

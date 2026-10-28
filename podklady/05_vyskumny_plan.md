# Výskumný plán — RQ, dizajn, kto/ako, baseline porovnanie

**DP:** Výskum vplyvu generických a adaptívnych nástrojov UI v školskom prostredí · FIIT STU
Tento dokument zastrešuje body z poznámok zo stretnutia, ktoré nepatria priamo pod otázky 1–4: **research question plan, kto a ako, „porovnať vzorku v čase vs. so skupinou pred-AI", IT overenie.**

---

## 0. Zhrnutie na jednu obrazovku (TL;DR)

- **3 výskumné otázky:** RQ1 *ako* sa AI používa (deskripcia + profily), RQ2 *aký vplyv* na schopnosti (experiment), RQ3 *aký mechanizmus* (mediácia offloadingu).
- **Dizajn:** 3-skupinový kvázi-experiment (adaptívna / generická AI / kontrola) s pre-testom a post-testom, doplnený o behaviorálne logy a kvalitatívne rozhovory.
- **Kľúčové rozhodnutie o porovnaní (čo zdvihol školiteľ):** „vzorka v čase" vs. „porovnanie so skupinou z čias bez AI". Rozoberám 3 varianty; **odporúčam synchrónnu kontrolnú skupinu + zapožičanie pred-AI noriem** namiesto neexistujúcej historickej vzorky.
- **Kto a ako:** žiaci 2.–3. ročníka, 1 sedenie 90 min (pilot) → prípadne 3–4 sedenia (longitudinálne jadro), nástroj/hra v prehliadači.

---

## 1. Research question plan (výskumné otázky a hypotézy)

Štruktúra odráža tri medzery z tvojej SOTA (self-report dominuje, hrubá typológia, SK podreprezentované) a tri vrstvy merania (Dokument 1).

### RQ1 — Ako slovenskí stredoškoláci reálne používajú nástroje UI?
*(deskriptívna, mapovacia — napĺňa „SK medzeru")*
- **H1a:** Existujú aspoň 3 odlíšiteľné profily používateľov (replikácia Tomczyka, ale na základe *správania*, nie len dotazníka).
- **H1b:** Profil používania sa líši podľa typu školy (gymnázium vs technická SOŠ).
- **Dáta:** logy z nástroja/hry + AI literacy + SAID + offloading škála.

### RQ2 — Aký vplyv má typ nástroja UI na schopnosti žiakov?
*(experimentálna, kauzálna — jadro práce)*
- **H2a:** Adaptívny nástroj prinesie vyšší vedomostný zisk než generická AI a kontrola (replikácia Kestina/Hariyanta).
- **H2b:** Skupina s generickou AI prejaví nižšie kritické zapojenie (kratší čas čítania, menej úprav, vyšší offloading) než adaptívna a kontrola (replikácia Kosmyny behaviorálne).
- **Dáta:** pre/post doménový test + CT batéria + behaviorálne logy. Analýza: ANCOVA + LMM (Dokument 3).

### RQ3 — Akým mechanizmom UI ovplyvňuje kritické myslenie?
*(vysvetľujúca — najvyššia pridaná hodnota)*
- **H3a:** Vzťah medzi používaním AI a kritickým myslením je mediovaný kognitívnym offloadingom (replikácia Gerlicha na SK stredoškolákoch).
- **H3b:** Vyššia dôvera v AI súvisí s nižším kritickým myslením; vyššia sebadôvera s vyšším (replikácia Lee et al.).
- **Dáta:** všetky škály + testy. Analýza: mediačný model + regresia (Dokument 3).

> **Prečo takto:** RQ1 funguje aj bez experimentu (poistka, ak experiment zlyhá na nábore), RQ2 je „titulok", RQ3 dá hĺbku aj pri null-result v RQ2. Tri RQ = tri nezávislé cesty k publikovateľnému výsledku.

---

## 2. Výskumný dizajn (kostra)

```
            ┌─ Skupina A: ADAPTÍVNY nástroj (hra/Khanmigo-štýl) ─┐
PRE-TEST ──┼─ Skupina B: GENERICKÁ AI (ChatGPT-štýl) ───────────┼── POST-TEST ── (odložený re-test)
            └─ Skupina C: KONTROLA (bez AI) ─────────────────────┘
   │                         │                                        │
   │                    [LOGY správania počas intervencie]            │
   └── doménový test + CT batéria + AI škály ──────────────────── ekvivalentné verzie ──┘
                                  │
                          [kvalitatívne rozhovory s podvzorkou]
```

- **Typ:** kvázi-experiment (triedy sa nedajú vždy plne randomizovať individuálne → randomizácia na úrovni tried alebo stratifikované priradenie).
- **Vzor:** Slijepcevic & Yaylali (3 skupiny) + Lee (logy) + Kosmyna (behaviorálne proxy) — presne tá kombinácia, ktorú odporúčaš v závere SOTA.
- **N:** ~18/skupina je štatistické minimum (power 0,8, stredný efekt); cieľ ~30–60/skupina kvôli výpadkom a porovnaniu škôl (Dokument 2, 3).

---

## 3. Kľúčové rozhodnutie: „vzorka v čase" vs. „porovnanie so skupinou pred AI"

Toto zdvihol školiteľ a je to **najdôležitejšie metodologické rozhodnutie celej práce.** Otázka znie: voči čomu meriame „vplyv"? Tri varianty:

### VARIANT 1 — Longitudinálne (tá istá vzorka v čase)
Tých istých žiakov meriam opakovane (pred intervenciou, po nej, s odstupom). „Vplyv" = zmena v čase.
- **Plusy:** každý žiak je sám sebe kontrolou → eliminuje individuálne rozdiely (ako Kestinov krížový dizajn, ako Kosmynove 4 mesiace). Najsilnejší dôkaz *zmeny*.
- **Mínusy:** vyžaduje viac sedení a čas (týždne–mesiace), riziko úbytku účastníkov (attrition), efekt opakovaného testovania (žiaci si pamätajú otázky → nutné ekvivalentné formy).

### VARIANT 2 — Historická / kohortová baseline (porovnanie so skupinou z čias pred AI)
Porovnám dnešných žiakov so skupinou z obdobia, keď AI ešte nebola.
- **Plusy:** priamo by odpovedalo na „čo nám AI urobila" — najatraktívnejšia otázka.
- **Mínusy:** ⚠️ **na Slovensku NEEXISTUJÚ pred-AI dáta** merané rovnakými nástrojmi na rovnakej populácii (tvoja SOTA to explicitne hovorí — prvý prieskum bol 2023, žiadny s validovaným psychometrickým nástrojom). Bez baseline dát sa historické porovnanie **nedá spraviť čisto** — líšili by sa kohorty, kurikulum, nástroje → neinterpretovateľné. Realizovateľné len ako *aproximácia*.

### VARIANT 3 — Synchrónna kontrola + zapožičané normy ⭐ (ODPORÚČANÝ HYBRID)
Namiesto neexistujúcej historickej vzorky použijem **kontrolnú skupinu „tu a teraz" bez AI** (zastupuje „pred-AI stav") **a navyše** porovnám výsledky s **publikovanými normami CT testov z pred-AI éry** (napr. staršie normy Ravena, HCTA, CRT z 2015–2020).
- **Plusy:** realizovateľné v jednom semestri, kontrolná skupina je metodologicky čistá náhrada za historickú baseline (rovnaká doba, rovnaké kurikulum, líši sa len AI), zapožičané normy dajú *orientačné* historické porovnanie bez zберu vlastných pred-AI dát.
- **Mínusy:** kontrolná skupina nie je „pred-AI" doslova (žiaci AI poznajú z bežného života) → meria *akútny* efekt nástroja, nie generačnú zmenu. Toto treba v limitáciách priznať.

### Hĺbkový „čo ak" rozbor — VARIANT 3

**ČO AK** ako „pred-AI náhradu" použijeme **synchrónnu kontrolnú skupinu** (rieši úlohy bez AI)
→ **DOSTANEME** čistý experimentálny kontrast bez nutnosti časovej mašiny. **Istota ~95 %**, že je to metodologicky obhájiteľnejšie než pseudo-historické porovnanie nesúrodých kohort.
→ **Interpretácia:** rozdiel medzi „AI skupinami" a kontrolou = *akútny efekt* prítomnosti nástroja pri úlohe.

**ČO AK** k tomu priložíme **longitudinálne jadro** (aspoň pre gymnaziálnu vzorku: pre-test, intervencia, post-test, odložený re-test o 3–4 týždne)
→ **DOSTANEME** Kosmynov efekt „kognitívneho dlhu" v malom — či sa rozdiel po čase prehĺbi alebo zmizne. **Istota ~70 %**, že pri 3–4 týždňoch zachytíme aspoň náznak retencie/jej straty; plný „dlh" Kosmyna videla až po 4 mesiacoch, čo je nad rámec jedného semestra.

**ČO AK** doplníme **zapožičané pred-AI normy** validovaných testov (Raven, CRT)
→ **DOSTANEME** orientačné zarámcovanie „kde sú dnešní žiaci voči populácii spred 5–10 rokov". **Istota ~60 %**, že normy budú dosť porovnateľné (pozor na jazyk a kohortové efekty — uvádzať len ako kontext, nie ako hlavný dôkaz).

**ČO AK** sa rozhodneme **NErobiť** čisté historické porovnanie (Variant 2)
→ **DOSTANEME** čistejšiu, obhájiteľnejšiu prácu. **Istota ~90 %**, že oponent by historické porovnanie nesúrodých kohort kritizoval ako neinterpretovateľné — vyhneme sa tomu vedome a zdôvodnene.

> **Veta pre školiteľa:** *„Historická pred-AI vzorka na SK neexistuje a porovnanie nesúrodých kohort by bolo neinterpretovateľné. Nahrádzam ju synchrónnou kontrolnou skupinou bez AI (čistý experimentálny kontrast) a longitudinálnym jadrom (zmena v čase), pričom pred-AI normy validovaných testov použijem len ako orientačný kontext. Tým mám aj experimentálnu kauzalitu, aj prvok zmeny v čase, bez metodologicky chybného historického porovnania."*

---

## 4. Kto a ako (konkrétne použitie)

### Kto
- **Hlavná populácia:** žiaci 2.–3. ročníka gymnázia (jadro) + technickej SOŠ (kontrast), 16–18 r. (Dokument 2).
- **Podvzorka na rozhovory:** ~6–10 žiakov z každej skupiny (kvalitatívne vysvetlenie — vzor Lee/Slijepcevic).
- **Učitelia:** 1 „šampión" na školu (koordinácia, nie meraná populácia v jadre; voliteľne replika AI Kompas dotazníka pre kontext).

### Ako (priebeh jedného sedenia, ~90 min)
1. **Úvod + súhlas** (5 min) — pseudonymizácia, žiak dostane kód (napr. ZK-014).
2. **Pre-test** (~35 min) — doménový test + CT batéria + AI škály (Dokument 1).
3. **Intervencia** (~35 min) — žiak rieši úlohy podľa skupiny:
   - A: adaptívny nástroj / hra v adaptívnom režime,
   - B: generický ChatGPT / hra v generickom režime,
   - C: bez AI (papier / hra v kontrolnom režime).
   Počas toho **nástroj/hra loguje** prompty, časy, úpravy, doplňujúce otázky.
4. **Post-test** (~15 min) — ekvivalentná forma + krátky dotazník vnímania.
5. *(Odložene, voliteľne)* re-test o 3–4 týždne.

### Technické „ako" (IT riešenie a overenie)
- **Dve cesty zberu** (rozhodne IT realita školy, Dokument 2 bod 3):
  - **(a) Hra v prehliadači** (`hra-demo/`) — žiadna inštalácia, žiadny proxy, beží offline, exportuje JSON. *Najnižšia bariéra, odporúčané pre gymnázium.*
  - **(b) Prompt-monitor nástroj** (existujúci Java/MITM proxy → migrácia na mitmproxy) — zachytáva *reálne* prompty pri voľnom používaní ChatGPT. *Vyššia ekologická validita, vyššia technická + etická bariéra; vhodné pre technickú SOŠ.*
- **Overenie pipeline (walking skeleton → produkcia):** stabilná CA, scoped MITM (len výskumné domény), pseudonymizácia pri zázname, šifrované úložisko, súhlasy/DPIA — všetko v roadmape README nástroja. Hra (a) tieto problémy *obchádza*, preto je dobrá poistka.

---

## 5. Etika a GDPR (začať OKAMŽITE — kritická cesta)
- Informovaný súhlas: **oddelene žiak + zákonný zástupca** (maloletí).
- **DPIA** (analýza vplyvu na ochranu údajov) — fínsky model to vyžaduje pre vzdelávacie AI nástroje; použiť ako vzor a argument.
- Schválenie **etickou komisiou FIIT** — môže trvať ~mesiac → **podať ako prvé.**
- Retenčná politika: surové logy zmazať do N dní po analýze, uchovať len agregáty.
- Vzor procedúry súhlasu/logovania: Slijepcevic & Yaylali (recenzované).

---

## 6. Harmonogram (návrh kritickej cesty)
| Fáza | Obsah | Pozn. |
|---|---|---|
| 1 | Etika + súhlasy + nábor škôl | **začať hneď** (najdlhšia čakacia doba) |
| 2 | Finalizácia + pilot meracej batérie a hry (~30 žiakov) | validácia (α, položky); riziková fáza |
| 3 | Ostrý zber (pre/post + logy) | 1–3 školy |
| 4 | Analýza (ANCOVA, mediácia, zhluky) + rozhovory | R/jamovi |
| 5 | Písanie + odporúčania pre prax | prepojiť na Plán 2025–2027 |

---

## Zdroje
- Power/N pre 3-skupinový dizajn: [G*Power návod](https://www.researchgate.net/publication/353583888_Sample_size_determination_and_power_analysis_using_the_GPower_software)
- Dizajnové vzory: Kestin (RCT crossover), Lee (logy + LMM), Gerlich (mediácia HCTA), Slijepcevic (3 skupiny + LPCI), Kosmyna (longitudinálne, behaviorálne) — tvoja SOTA kapitola.
- Pred-AI normy testov (kontext): [APM SK (Psychodiagnostika)](https://psychodiagnostika.sk/produkt/t-224-ravenove-progresivne-matice-pre-pokrocilych/), CRT — [HKU](https://philosophy.hku.hk/think/critical/tests.php).
- Etika/DPIA vzor: Fínsko — z tvojej SOTA (finland2025aieducation).

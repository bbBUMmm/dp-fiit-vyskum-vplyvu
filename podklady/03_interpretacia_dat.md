# Otázka 3 — Ako konkrétne interpretovať nazbierané dáta

**DP:** Výskum vplyvu generických a adaptívnych nástrojov UI v školskom prostredí · FIIT STU

---

## 0. Zhrnutie na jednu obrazovku (TL;DR)

- Máme **4 zdroje dát**: (1) pre/post testy, (2) self-report škály, (3) behaviorálne logy z nástroja/hry, (4) kvalitatívne odpovede/rozhovory. Interpretácia = ich **triangulácia**.
- **Hlavná analýza výsledku:** **ANCOVA** (post-test ako závislá, skupina ako faktor, pre-test ako kovariát) — nie obyčajný t-test rozdielov. Doplnkovo **normalizovaný zisk g** (Hake) a **Cohenovo d** (effect size).
- **Tri „príbehy“, ktoré dáta môžu rozprávať** = 3 varianty interpretačného rámca nižšie.
- **Odporúčaný = Variant C: „mechanizmus“** (mediačný + zhlukový model) — nielen *či* AI pomáha, ale *prečo a komu*.
- Každú interpretáciu uvádzam s **konkrétnym očakávaným výsledkom a istotou** (metóda „čo ak“).

---

## 1. Od surových dát k interpretácii — dátová architektúra

Pripomenutie vektora na žiaka (z Dokumentu 1):
```
žiak_id, skupina ∈ {adaptívny, generický, kontrola}, typ_školy,
  domena_pre, domena_post,
  CT_pre, CT_post, CRT,
  MAI, offloading, AI_literacy, trust_AI, raven_kontrola,
  LOGY: pocet_promptov, dlzka_promptu, cas_citania, miera_uprav_%, doplnujuce_otazky
```

**Tri odvodené metriky zisku** (počítaš z pre/post):
1. **Surový zisk** = post − pre. (Jednoduché, ale skreslené východiskovou úrovňou.)
2. **Normalizovaný zisk g (Hake)** = (post − pre) / (max − pre). Interpretácia: **g > 0,7 vysoký, 0,3–0,7 stredný, < 0,3 nízky.** Toto je štandard v *concept inventory* výskume — komisia ho pozná.
3. **Cohenovo d** = (M_post − M_pre) / SD_pooled. Štandardizovaný effect size, **porovnateľný so SOTA** (Kestin uvádzal d, Harvard mal d ≈ 0,7–1,3). Interpretácia: **0,2 malý, 0,5 stredný, 0,8 veľký.**

> **Prečo dve metriky:** g je dobrý na relatívne zlepšenie, ale je citlivý na extrémy (malý posun pri vysokom skóre a veľký posun pri nízkom dajú podobné g). d je stabilnejší. **Uvádzaj obe** — to je znak metodologickej zrelosti a presne to robia kvalitné PER (physics education research) štúdie.

---

## 2. Hlavné štatistické nástroje a *ako ich interpretovať* (nie len ktoré)

### (a) Porovnanie 3 skupín na výsledku → ANCOVA
- **Model:** `post-test ~ skupina + pre-test(kovariát) [+ raven + typ_školy]`
- **Prečo ANCOVA a nie t-test/ANOVA na rozdieloch:** ANCOVA odfiltruje vstupné rozdiely a má vyššiu silu. **Dôležitá pasca (z literatúry):** efekt intervencie sa interpretuje ako rozdiel skupín **na post-teste pri kontrole pre-testu**, NIE ako priemer pre+post. Toto je častá chyba — vyhneme sa jej.
- **Čo „vypadne“:** F-štatistika + p-hodnota (je rozdiel medzi skupinami?) + **adjustované priemery** (kde leží ktorá skupina po očistení) + **parciálne η²** (effect size).
- **Ako interpretovať:** „Po kontrole vstupných vedomostí skupina s adaptívnym nástrojom dosiahla významne vyšší post-test než kontrola (F(2, N)=…, p<0,05, η²=…), zatiaľ čo generický ChatGPT sa od kontroly nelíšil“ — *toto je presne typ vety, ktorý chceš vedieť napísať.*

### (b) Zmena v čase + interakcia → zmiešaná ANOVA / lineárny zmiešaný model (LMM)
- Keď máš opakované merania (pre, post, prípadne odložený re-test): `skóre ~ čas × skupina + (1|žiak)`.
- **Kľúčový efekt = interakcia čas × skupina:** rozdielne *strmosti* zlepšenia medzi skupinami. Toto je „dôkaz vplyvu“.
- LMM s náhodným interceptom na žiaka je presne to, čo použil **Lee et al.** (random-intercepts regression) — dáš si ho do práce ako „metóda prevzatá z Lee 2025“.

### (c) Vzťahy medzi premennými → korelácia + viacnásobná regresia
- Replikácia Gerlicha/Lee: `CT_post ~ trust_AI + self_confidence + offloading + frekvencia_AI`.
- **Očakávaný smer (hypotézy z SOTA):** trust_AI ↓ kritické myslenie; self-confidence ↑ kritické myslenie; offloading ↓ kritické myslenie.

### (d) Mechanizmus → mediačná analýza
- Gerlichov objav: AI → offloading → ↓ kritické myslenie. Offloading je **mediátor**.
- Postup: Baron-Kenny + **bootstrapping nepriameho efektu** (presne ako Gerlich). Moderné: `mediation`/`lavaan` v R, alebo PROCESS makro.
- **Čo to dá:** vetu „efekt používania AI na kritické myslenie je z X % sprostredkovaný kognitívnym offloadingom“ — kauzálne najsilnejší výsledok, aký vieš dať.

### (e) Profily žiakov → zhluková analýza
- Replikácia Tomczyka (3 profily učiteľov). U teba: zhlukni žiakov podľa logov + self-reportov → napr. „kritickí overovatelia“, „pasívni preberatelia“, „selektívni používatelia“.
- Metóda: k-means / hierarchické zhlukovanie na štandardizovaných premenných; počet zhlukov cez siluetu/elbow.
- **Toto je tvoj originálny príspevok** — detailnejšia typológia, než akú má ktorákoľvek SOTA štúdia, lebo ju staviaš na *reálnom správaní*, nie len na dotazníku.

### (f) Behaviorálne logy → odvodené ukazovatele (náhrada za Kosmynovo EEG)
- **Inter-prompt interval** (čas medzi promptami) → krátky = „vzorec krátkej pamäte“, impulzívne preberanie.
- **Čas čítania odpovede** → proxy hĺbky spracovania (Kosmyna ukázala, že LLM skupina si nepamätala vlastné eseje — krátky čas čítania to predpovedá).
- **Miera úprav výstupu (%)** → indikátor kritického zapojenia (preberá doslovne vs. prepracúva).
- **Počet doplňujúcich otázok** → indikátor hĺbky porozumenia / sokratického vs. „daj odpoveď“ použitia.
- **Interpretácia:** tieto metriky koreluj s testovým ziskom a so škálami → ak „pasívni preberatelia“ (krátke čítanie, 0 úprav) majú nižší zisk, máš **behaviorálny dôkaz** offloadingu.

### (g) Kvalitatívne dáta → tematická analýza
- Otvorené odpovede/rozhovory (ako Lee, Slijepcevic): nezávislé kódovanie 2 hodnotiteľmi, medzihodnotiteľská zhoda (Cohenovo κ), konsolidácia tém.
- Slúži na **vysvetlenie** kvantitatívnych nálezov (prečo Khanmigo skupina oceňovala sokratický prístup, hoci skóre boli rovnaké).

---

## 3. Tri varianty interpretačného rámca

> Tri rôzne „príbehy“, ktoré z tých istých dát vieš vyrozprávať. Líšia sa ambíciou a rizikom.

### VARIANT A — „Porovnávací“ (Pomáha AI, a ktorá?)
Hlavná otázka: *Ktorá skupina sa zlepšila najviac?* Nástroje: ANCOVA + g + d. Výstup: rebríček skupín.
- **Plusy:** jednoduché, jednoznačné, ľahko obhájiteľné, priamo porovnateľné s Kestinom/Slijepcevicom.
- **Mínusy:** povrchné — nepovie *prečo*. Riziko „null result“ (Slijepcevic nenašiel rozdiel medzi Khanmigo a Google) → ak vyjde nula, príbeh je chudobný.

### VARIANT B — „Koreláčný/prediktívny“ (Čo súvisí s čím?)
Hlavná otázka: *Aké faktory predpovedajú kritické myslenie / zisk?* Nástroje: korelácie, viacnásobná regresia, LMM.
- **Plusy:** bohaté na vzťahy, replikuje Gerlicha/Lee, funguje aj keď skupiny nevyjdú rozdielne.
- **Mínusy:** korelácia ≠ kauzalita (musíš to priznať). Bez experimentálnej manipulácie slabšie tvrdenia.

### VARIANT C — „Mechanizmus a profily“ ⭐ (ODPORÚČANÝ)
Hlavná otázka: *Prečo a komu AI (ne)pomáha?* Spája všetko: ANCOVA (či) → mediácia (prečo, cez offloading) → zhluky (komu, ktoré profily) → logy (behaviorálny dôkaz) → kvalitatíva (ľudské vysvetlenie).
- **Plusy:** najvyššia vedecká hodnota, **odolný voči null-result** (aj keď skupiny nevyjdú, mediácia a profily dajú príbeh), napĺňa všetky 3 medzery z tvojej SOTA (behaviorálne dáta, jemná typológia, slovenský kontext). Triangulácia = silná validita.
- **Mínusy:** najnáročnejší na analýzu a interpretáciu, potrebuje dostatočné N pre mediáciu/zhluky (orientačne ≥ 60–80 spolu), vyžaduje zvládnuť R/jamovi/SPSS na pokročilejšej úrovni.

---

## 4. Výber a hĺbkový „čo ak“ rozbor — VARIANT C

Vyberám **Variant C**. Veta: je jediný, ktorý ti dá publikovateľný príbeh **aj keď hlavné porovnanie skupín vyjde ako null** (čo je u Slijepcevica reálne nastalo) — a zároveň využije tvoje unikátne behaviorálne dáta.

### Reťaz „čo ak“ — predikcia výsledkov a ich interpretácie

**ČO AK** ANCOVA ukáže, že **adaptívny nástroj > generický ≈ kontrola** na vedomostnom zisku
→ **INTERPRETÁCIA:** potvrdzuje Kestina/Hariyanta — *dizajn* nástroja (sokratický, pedagogický) rozhoduje, nie samotná „AI“. **Istota ~60 %, že to vyjde takto** (adaptívny mierne lepší), lebo to zodpovedá literatúre, ale efekt môže byť malý.
→ **Akčný dôsledok:** odporúčanie pre školy „nasadzujte pedagogicky navrhnuté nástroje, nie holý ChatGPT“.

**ČO AK** ANCOVA ukáže **žiadny rozdiel medzi skupinami** (null result, ako Slijepcevic)
→ **TOTO NIE JE ZLYHANIE.** Interpretácia: krátkodobé vedomostné zisky sú podobné, **rozdiel je inde** — v *spôsobe* používania a v offloadingu. **Istota ~40 %**, že hlavný efekt bude nesignifikantný pri realistickom N. **A práve preto máme Variant C** — príbeh sa presunie na mediáciu a profily.

**ČO AK** mediačná analýza potvrdí **AI použitie → ↑ offloading → ↓ CT_post**
→ **INTERPRETÁCIA:** replikujeme Gerlicha na slovenských stredoškolákoch — prvý raz. **Istota ~70 %**, že nepriamy efekt cez offloading bude signifikantný, ak vzorka ≥ ~80 a offloading dobre zmeriame; toto je v súlade s 2 nezávislými štúdiami (Gerlich self-report, Kosmyna EEG).
→ **Toto je hlavný „titulkový“ výsledok práce.**

**ČO AK** zhluková analýza nájde **3 profily** (kritickí overovatelia / selektívni / pasívni preberatelia)
→ **INTERPRETÁCIA:** „pasívni preberatelia“ majú vysoký trust_AI, krátky čas čítania, 0 úprav, najnižší zisk; „overovatelia“ opak. **Istota ~75 %**, že aspoň 2–3 zmysluplné profily vzniknú (Tomczyk našiel 3, ľudská variabilita to takmer zaručuje).
→ **Akčný dôsledok:** cielené odporúčania — škola má učiť *ako* používať AI (prejsť žiakov z „preberateľov“ na „overovateľov“).

**ČO AK** behaviorálne logy korelujú s testovým ziskom (krátke čítanie + 0 úprav → nízky zisk)
→ **INTERPRETÁCIA:** máme **lacný, škálovateľný proxy kognitívneho zapojenia** — to, čo Kosmyna robila EEG-čkom za tisíce eur. **Istota ~85 %**, že aspoň *čas čítania* alebo *miera úprav* bude korelovať so ziskom (silný teoretický podklad).
→ **Toto je tvoj metodologický príspevok** — validácia behaviorálnych proxy proti testovým výsledkom.

**ČO AK** trust_AI (SAID) negatívne koreluje s CT, ale self-confidence pozitívne
→ **INTERPRETÁCIA:** presná replikácia Lee et al. (CHI 2025) na slovenských žiakoch. **Istota ~70 %.** Posilní to celý príbeh konzistentnosťou s top-tier štúdiou.

### Ako vyzerá „výsledková“ kapitola (kostra, ktorú dáta naplnia)
1. **Deskriptíva** — tabuľka priemerov/SD na skupinu a typ školy.
2. **H1 (porovnanie):** ANCOVA na vedomostnom zisku → adjustované priemery + η² + g + d.
3. **H2 (myslenie):** zmena CT/MAI v čase × skupina (LMM).
4. **H3 (mechanizmus):** mediačný model offloadingu (bootstrap CI nepriameho efektu).
5. **H4 (profily):** zhluky + ich charakteristika cez logy a škály.
6. **H5 (validácia proxy):** korelácie logy ↔ zisk ↔ self-report.
7. **Kvalitatívne vysvetlenie:** témy z rozhovorov, ktoré osvetľujú H1–H5.

---

## 5. Praktické nástroje a reprodukovateľnosť
- **Softvér:** R (`tidyverse`, `lme4`, `lavaan`/`mediation`, `psych`, `cluster`) — zadarmo, reprodukovateľné, skriptovateľné. Alternatíva **jamovi** (GUI, zadarmo, čo použil aj Slijepcevic) alebo SPSS (ak ho má fakulta).
- **Reprodukovateľnosť (zadanie DP to vyžaduje):** všetky skripty + anonymizované dáta do repozitára; analýza ako *literate* dokument (R Markdown/Quarto) → každý graf má kód.
- **Pseudonymizácia:** logy ukladať s `deviceHash` (HMAC), nikdy nie meno/IP — tvoj nástroj na to už má roadmapu (README).
- **Chýbajúce dáta a výpadky:** dopredu definuj pravidlo (napr. žiak musí mať pre aj post; mnohonásobná imputácia len ak < 10 % chýba).

---

## 6. Čo povedať školiteľovi (zhrnutie)

> **„Dáta nebudem interpretovať len ako ‚ktorá skupina vyhrala‘. Hlavná analýza je ANCOVA s pre-testom ako kovariátom, doplnená normalizovaným ziskom a Cohenovým d kvôli porovnateľnosti so SOTA. Ale ťažisko interpretácie je mechanizmus: mediačným modelom otestujem, či AI znižuje kritické myslenie cez kognitívne offloading (replikácia Gerlicha), zhlukovou analýzou nájdem profily žiakov podľa reálneho správania (jemnejšie než Tomczyk), a behaviorálne logy z nástroja použijem ako lacný proxy kognitívneho zapojenia namiesto Kosmynovho EEG. Tým mám príbeh aj v prípade, že hlavné porovnanie skupín vyjde ako nesignifikantné — čo sa Slijepcevicovi reálne stalo.“**

---

## Zdroje
- Normalizovaný zisk (Hake) a interpretácia g: [APS — prečo používať normalizovaný zisk](https://link.aps.org/pdf/10.1103/PhysRevPhysEducRes.16.010108), [APS PER](https://journals.aps.org/prper/pdf/10.1103/PhysRevPhysEducRes.14.010115)
- Cohenovo d, ANCOVA pasca (post pri kontrole pre): [APS PER metodológia](https://journals.aps.org/prper/pdf/10.1103/PhysRevPhysEducRes.14.010115)
- Power analýza 3 skupiny (18/skupina pri strednom efekte): [G*Power návod (RG)](https://www.researchgate.net/publication/353583888_Sample_size_determination_and_power_analysis_using_the_GPower_software), [IES — power analysis in education](https://ies.ed.gov/ies/2025/01/power-analysis-education-research)
- Mediácia + bootstrapping, random-intercepts regresia: metodológie z tvojej SOTA — Gerlich (Societies 2025), Lee et al. (CHI 2025)
- Concept inventory pre/post best practices: [PhysPort](https://www.physport.org/expert/AdministeringConceptInventories/)

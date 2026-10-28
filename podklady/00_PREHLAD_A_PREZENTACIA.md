# 📍 PREHĽAD — podklady na stretnutie so školiteľom

**DP:** Výskum vplyvu generických a adaptívnych nástrojov UI v školskom prostredí
**Školiteľ:** Ing. Miroslav Bahleda, PhD. · FIIT STU
**Toto je úvodný dokument — prečítaj prvý.** Mapuje všetky odpovede a dáva scenár prezentácie.

---

## Čo je v tomto priečinku

| Súbor | Otázka zo stretnutia | Čo obsahuje |
|---|---|---|
| **00_PREHLAD_A_PREZENTACIA.md** | — | tento prehľad + scenár prezentácie |
| **01_meranie_kognitivnych_schopnosti.md** | Ako merať kognitívne schopnosti? | katalóg nástrojov (HCTA, Watson-Glaser, MAI, offloading, AI literacy, Raven…), 3 varianty, výber |
| **02_vyber_skol.md** | Na ktoré školy ísť? | profily SK škôl, 3 varianty, výber + páka cez STU |
| **03_interpretacia_dat.md** | Ako interpretovať dáta? | štatistika (ANCOVA, mediácia, zhluky), 3 varianty, „čo ak" predikcie |
| **04_hra_navrh.md** | Hra s uzavretými možnosťami? | návrh „AI Detektív", 6 typov otázok s príkladmi, 3 varianty |
| **05_vyskumny_plan.md** | RQ, kto/ako, baseline | výskumné otázky, dizajn, „vzorka v čase vs. pred-AI", etika |
| **hra-demo/index.html** | (implementácia hry) | **spustiteľné demo** — dvojklik, beží offline |

Každý dokument má rovnakú štruktúru, ako si žiadal: **3 varianty → výber jedného → hĺbkový rozbor metódou „čo ak"** (čo ak skúsime X → dostaneme Y, s odhadom istoty).

---

## ⭐ Odporúčané odpovede (jednou vetou na otázku)

1. **Meranie:** hybridná batéria o 4 vrstvách — vedomostný zisk (concept inventory) + kritické myslenie (vlastná batéria na 5 Halpernových dimenzií, HCTA *nekupovať*) + vzťah k AI (voľné škály: Gerlich offloading, SAID, AI literacy) + **behaviorálne logy** ako lacná náhrada Kosmynovho EEG. Plné IQ **nie**, Raven len ako kontrolná premenná.

2. **Školy:** jadro = **gymnázium, 2.–3. ročník, matematika/informatika** (najčistejšia interpretácia) + **1 technická SOŠ** ako kontrast → originálna otázka „líši sa vplyv AI podľa typu školy?". Páka: STU ako národné kompetenčné centrum.

3. **Interpretácia:** nie „ktorá skupina vyhrala", ale **mechanizmus** — ANCOVA (či) → mediácia offloadingu (prečo, replikácia Gerlicha) → zhluky profilov (komu, jemnejšie než Tomczyk) → logy ako behaviorálny dôkaz. Odolné voči null-result.

4. **Hra:** **„AI Detektív"** — žiak rieši prípady s AI, ktorá *občas klame*; pri každom kroku volí z uzavretých možností (uver/over/spýtaj sa/odmietni) → automatické skóre po dimenziách. Tri režimy = tri experimentálne skupiny. **Funkčné demo priložené.**

5. **Dizajn/baseline:** 3-skupinový kvázi-experiment (pre/post + logy). Historickú „pred-AI" vzorku (neexistuje na SK) **nahrádzam synchrónnou kontrolnou skupinou** + longitudinálnym jadrom; pred-AI normy len ako kontext.

---

## 🎤 Scenár prezentácie (~15–20 min)

**1) Rámec (2 min).** „Zo stretnutia vyplynuli 4 konkrétne otázky + dizajnové rozhodnutie. Ku každej mám 3 varianty a jeden rozobratý do hĺbky. Ukotvil som ich v našej SOTA — všetko nadväzuje na päť štúdií, ktoré už máme (Kestin, Lee, Gerlich, Slijepcevic, Kosmyna)."

**2) Meranie (3 min).** Ukáž tabuľku 4 vrstiev (Dok. 1, §5). Kľúčová pointa: *„HCTA nekupujeme — je komerčný a anglický; použijeme ho ako teoretický rámec a postavíme vlastnú validovanú batériu. Plné IQ nemeriame, lebo neodpovedá na naše otázky — Raven len ako kontrola."*

**3) Školy (2 min).** Gymnázium-jadro + technická SOŠ-kontrast. Pointa: *„Väčšina SK stredoškolákov je na SOŠ, no vo výskume AI sú podreprezentovaní — kontrast gymnázium/SOŠ je originálny."*

**4) Hra — LIVE DEMO (4 min).** Otvor `hra-demo/index.html`. Zahraj 2–3 uzly (ukáž halucináciu — napr. „obsah kruhu = 2πr" alebo „Bratislava 2,3 mil."). Dojdi na obrazovku výsledkov → ukáž **radar + offloading index + JSON export**. Pointa: *„Toto rieši problém otvorených promptov — uzavreté voľby sa skórujú samé a idú priamo do štatistiky."*

**5) Interpretácia (3 min).** Diagram H1–H5 (Dok. 3, §4). Pointa: *„Máme príbeh aj keď hlavné porovnanie vyjde nulové — ako sa stalo Slijepcevicovi. Ťažisko je mechanizmus: offloading ako mediátor."*

**6) Dizajn + baseline (2 min).** Pointa o „pred-AI vzorke": *„Neexistuje, nahrádzam ju kontrolnou skupinou + longitudinálnym jadrom — čisté a obhájiteľné."*

**7) Otvorené rozhodnutia + ďalší krok (2 min).** Zoznam nižšie.

> **Tip:** demo si pred prezentáciou otvor a klikni ním raz, nech vieš, kde čo je. Funguje bez internetu.

---

## ❓ Otvorené rozhodnutia pre školiteľa (toto sa ho spýtaj)

1. **Doména vedomostného testu** — matematika, fyzika, alebo odborný predmet SOŠ? (Určuje výber concept inventory.)
2. **Longitudinálne vs. jednorazovo** — máme čas/kapacitu na 3–4 sedenia, alebo 1 sedenie? (Určuje, či zmeriame „kognitívny dlh".)
3. **Hra vs. prompt-monitor nástroj** — primárny zberný kanál? (Hra = nízka bariéra; proxy = vyššia ekologická validita.)
4. **Rozsah** — 1 gymnázium (čisté, isté) vs. + technická SOŠ (originálne, rizikovejšie na nábor)?
5. **Validácia batérie** — súhlas s pilotom ~30 žiakov pred ostrým zberom? (Kritické pre validitu.)

---

## ⚠️ Riziká a poistky (maj pripravené, ak sa spýta)

| Riziko | Poistka |
|---|---|
| Nezíska sa technická SOŠ | Fallback na čisté gymnázium (Dok. 2) — práca ostáva validná |
| Vlastná CT batéria má slabú reliabilitu | Fallback: Cornell Level X / Ennis-Weir + CRT (Dok. 1) |
| Hlavné porovnanie skupín = null result | Príbeh sa presunie na mediáciu + profily (Dok. 3, Variant C) |
| Adaptívny LLM/API zlyhá pri nasadení | Hra beží v „mock AI" režime offline (Dok. 4, §8) |
| Etika/súhlasy meškajú | Začať OKAMŽITE — najdlhšia kritická cesta (Dok. 5, §5) |
| Krátkodobý efekt = malý | Longitudinálne jadro + behaviorálne logy zachytia aj jemné rozdiely |

---

## 🔗 Ako to celé visí na existujúcej práci (kontinuita so SOTA)

- **Kestin** → adaptívny nástroj s pedagogickým dizajnom (skupina A v hre).
- **Lee** → logy + 6 aspektov kognitívneho úsilia + LMM (typy otázok v hre, analýza).
- **Gerlich** → offloading ako mediátor + HCTA rámec (RQ3, meracia vrstva C).
- **Slijepcevic** → 3-skupinový dizajn + interakčné logy (kostra experimentu).
- **Kosmyna** → behaviorálne proxy namiesto EEG (logy: čas čítania, úpravy) + longitudinálny prvok.

**Nič nezahadzujeme — všetko sú konkrétne kroky nad rámcom, ktorý už v práci je.** Praktická časť (prompt-monitor nástroj) ostáva, hra ho dopĺňa ako nízkobariérovú alternatívu a zároveň ako merací nástroj.

---

## ✅ Stav rozpracovania (čo je hotové dnes v noci)
- [x] Research: 13+ validovaných nástrojov merania (kritické myslenie, metakognícia, AI škály, IQ)
- [x] Research: slovenský školský systém (233 gymnázií, 437 SOŠ, štatistiky)
- [x] 5 hĺbkových dokumentov (3 varianty + „čo ak" rozbor v každom)
- [x] **Funkčné demo hry** (14 úloh, 6 dimenzií, 3 režimy, radar, JSON export) — otestované (`node test.js`, `node sim.js`)
- [ ] **Na rozhodnutie so školiteľom:** 5 otvorených bodov vyššie
- [ ] **Ďalší krok:** etika + nábor škôl (kritická cesta), pilot batérie a hry

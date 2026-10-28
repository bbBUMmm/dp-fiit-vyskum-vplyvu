# Otázka 4 — Hra s uzavretými možnosťami na meranie schopností

**DP:** Výskum vplyvu generických a adaptívnych nástrojov UI v školskom prostredí · FIIT STU
**Súvisí s:** spustiteľné demo v `podklady/hra-demo/index.html` (Dokument: implementácia)

---

## 0. Zhrnutie na jednu obrazovku (TL;DR)

- **Problém, ktorý hra rieši:** tvoje doterajšie riešenie zbiera **otvorené** odpovede (prompty) → ťažko sa kvantifikujú a porovnávajú. Hra prevedie schopnosti na **uzavreté voľby** → každá voľba = číslo → okamžitá, objektívna, porovnateľná analýza.
- **Odporúčaná hra: „AI Detektív“** — žiak rieši prípad/úlohu s pomocou AI asistenta, ktorý **občas klame** (halucinuje, používa nedôveryhodné zdroje, robí logické chyby). Žiak sa pri každom kroku rozhoduje z uzavretých možností: *uver / over / opýtaj sa zdroja / odmietni*. Tým **priamo meriame kritické myslenie voči AI.**
- **Každá voľba mapuje na dimenziu** (Halpernových 5 + Leeho 6 aspektov + offloading). Skóre sa počíta automaticky.
- **3 režimy hry = 3 experimentálne skupiny:** adaptívny AI (prispôsobuje obtiažnosť) / generický AI (statický) / kontrola (bez AI nápovedy). **Hra je teda zároveň meracím nástrojom aj intervenciou.**
- Nižšie: 3 varianty hry, výber, **6 typov otázok s konkrétnymi príkladmi**, skórovací model, „čo ak“ rozbor a popis demo implementácie.

---

## 1. Prečo hra (a prečo uzavreté možnosti)

| Otvorené otázky (doterajší stav) | Uzavreté možnosti (hra) |
|---|---|
| Žiak napíše prompt → bohaté, ale ťažko porovnateľné | Žiak vyberie z 4 možností → priamo číslo |
| Skórovanie vyžaduje ľudského kódera + medzihodnotiteľskú zhodu | Skórovanie automatické, 100 % objektívne |
| Veľký rozptyl, ťažká štatistika | Malý, riadený priestor → silná štatistika pri menšom N |
| Meria *čo* žiak napísal | Meria *aké rozhodnutie* žiak urobil v definovanej situácii |

> **Kľúčová myšlienka:** hra je **„donútenie do menšieho spektra“** (tvoja formulácia) — namiesto nekonečného priestoru promptov dáme žiakovi riadené dilemy, kde každá voľba má známu „kritickomysliteľskú hodnotu“. To je presne to, čo robí *forced-choice* časť HCTA, len v hernej, pútavej forme.

---

## 2. Tri varianty hry

### VARIANT 1 — „AI Detektív“ (kritické hodnotenie AI výstupov) ⭐ odporúčaný
Žiak je vyšetrovateľ/novinár/vedec a rieši prípad. AI asistent mu dáva indície a odpovede — **niektoré sú správne, niektoré sú nenápadné halucinácie / nedôveryhodné zdroje / logické klamy.** Žiak sa rozhoduje, či a ako AI dôverovať.
- **Meria:** verifikáciu vs. offloading, analýzu argumentov, dôveryhodnosť zdrojov, detekciu halucinácií — t. j. **presne tému DP.**
- **Plusy:** témovo dokonale sedí (kritické myslenie voči AI), uzavreté voľby sa skvele skórujú, ľahko gamifikovateľné (príbeh, skóre, „dôkazová tabuľa“), prirodzene podporuje 3 režimy (adaptívny/generický/kontrola).
- **Mínusy:** treba ručne pripraviť kvalitné položky (vrátane „pascí“) a overiť ich obtiažnosť na pilote.

### VARIANT 2 — „Architekt argumentu“ (stavanie a vyvracanie argumentov)
Žiak dostane tézu a z ponuky **skladá argument** výberom tvrdení, dôkazov a protiargumentov — niektoré sú silné, niektoré sú klamy (slamený panák, ad hominem, falošná dilema). AI navrhuje „stavebné kocky“, žiak ich hodnotí.
- **Meria:** analýzu argumentov, logické klamy (Halpern dim 2, Watson-Glaser hodnotenie argumentov).
- **Plusy:** veľmi „čisté“ meranie jednej dimenzie, ľahká validácia.
- **Mínusy:** užšie (hlavne argumentácia), menej príbehové, môže pôsobiť ako test.

### VARIANT 3 — „Vetviaci simulátor rozhodnutí“ (choose-your-path s AI)
Vetviaci príbeh: žiak čelí reálnym školským/životným situáciám s AI a robí uzavreté rozhodnutia; ďalší obsah sa **adaptuje** podľa volieb. (Napr.: blíži sa odovzdanie projektu, AI ponúka hotové riešenie — čo spravíš?)
- **Meria:** rozhodovanie, pravdepodobnostné uvažovanie, etiku/integritu, sklon k offloadingu.
- **Plusy:** najpútavejšie, prirodzene adaptívne, meria aj postoje a etiku.
- **Mínusy:** vetvenie skomplikuje porovnateľnosť (rôzni žiaci vidia rôzne cesty) → ťažšia štatistika; treba navrhnúť tak, aby kľúčové „meracie“ uzly videli všetci.

---

## 3. Výber a hĺbkový „čo ak“ rozbor — VARIANT 1 „AI Detektív“

Vyberám **Variant 1**, s **kľúčovými meracími uzlami spoločnými pre všetkých** (požičané z čistoty Variantu 2) a **jedným adaptívnym režimom** (požičané z Variantu 3). Veta: AI Detektív meria presne to, o čom je DP — schopnosť kriticky narábať s AI — a robí to uzavretými voľbami, ktoré sa skórujú samé.

### Herný cyklus (loop)
1. **Brief:** žiak dostane úlohu/prípad (napr. „Over, či je toto tvrdenie pravdivé a priprav krátku odpoveď.“).
2. **AI ťah:** AI asistent poskytne odpoveď/indíciu/zdroj. (V demo: „mock AI“ z vopred pripravenej banky; v ostrej verzii adaptívny režim volá reálny LLM.)
3. **Rozhodovací uzol:** žiak vyberie z 3–4 uzavretých možností (uver / over / spýtaj sa na zdroj / odmietni …).
4. **Dôsledok + mikrospätná väzba:** hra ukáže následok voľby (našiel pravdu / naletel halucinácii). Pri adaptívnom režime sa obtiažnosť ďalšieho uzla prispôsobí.
5. **Záznam:** uloží sa voľba, čas rozhodnutia, počet použitých nápovied, či žiak „odovzdal“ prácu AI.
6. Opakuj 10–15 uzlov → **profil žiaka** (skóre po dimenziách) + export JSON.

### Reťaz „čo ak“ (predikcia a istota)

**ČO AK** každý rozhodovací uzol napevno priradíme k jednej dimenzii a k „správnej“ kritickej voľbe
→ **DOSTANEME** automatické, objektívne skóre po dimenziách bez ľudského kódera. **Istota ~99 %**, že skórovanie bude reliabilné (uzavreté voľby → nulová hodnotiteľská chyba). Toto je hlavná výhoda oproti otvoreným promptom.

**ČO AK** do banky úloh zámerne vložíme **halucinácie a nedôveryhodné zdroje** (časť AI odpovedí je nesprávna)
→ **DOSTANEME** schopnosť rozlíšiť „slepých preberateľov“ od „overovateľov“ — kľúčový kontrast celej práce. **Istota ~90 %**, že rozptyl vo voľbách bude dosť veľký na zmysluplnú analýzu (žiaci sa reálne líšia v dôverčivosti). **Dôležité:** pomer správne/nesprávne treba kalibrovať (~50/50), inak sa dá hra „prejsť“ stratégiou „vždy over“ alebo „vždy ver“.

**ČO AK** zavedieme **3 režimy** (adaptívny/generický/kontrola) ako tri verzie tej istej hry
→ **DOSTANEME** intervenciu aj meranie v jednom nástroji — hra je zároveň „experimentálna podmienka“ aj „test“. **Istota ~95 %**, že to technicky zvládneme (líši sa len AI vrstva, meracie uzly ostávajú rovnaké).
→ **Adaptívny:** obtiažnosť/ústretovosť AI sa mení podľa výkonu (ako Khanmigo). **Generický:** AI odpovedá staticky (ako ChatGPT). **Kontrola:** žiak rieši rovnaké uzly **bez AI nápovedy** (len vlastný úsudok) → baseline.

**ČO AK** meriame aj **čas rozhodnutia a sklon „opýtať sa AI“**
→ **DOSTANEME** behaviorálne proxy offloadingu priamo v hre (rýchle, bezmyšlienkovité „uver“ = offloading). **Istota ~85 %**, že čas a počet nápovied budú korelovať s testovým offloadingom a CT skóre — máme internú validáciu.

**ČO AK** hru použijeme aj na **pre-test/post-test** (ekvivalentné verzie A/B banky úloh)
→ **DOSTANEME** meranie zmeny kritického narábania s AI pred/po intervencii v jednom konzistentnom nástroji. **Istota ~80 %**, že ekvivalentné formy vieme vytvoriť (rovnaká štruktúra, iné konkrétne prípady) — treba ich vyvážiť na pilote.

**ČO AK** sa AI vrstva (adaptívny režim) pri ostrom nasadení pokazí / nebude API
→ **FALLBACK:** hra beží v „mock AI“ režime z lokálnej banky úloh (presne ako demo) → experiment pokračuje, len adaptívna skupina splynie s generickou. **Vždy funkčná offline.**

---

## 4. Šesť typov otázok s KONKRÉTNYMI príkladmi

Každý typ = uzavretá voľba → mapovanie na dimenziu → skórovanie. Toto je „srdce“ — banka takýchto položiek tvorí hru.

### Typ 1 — Kalibrácia dôvery (offloading vs. verifikácia) · Lee „evaluate“, offloading
> **Situácia:** Pýtaš sa AI: *„Koľko obyvateľov má Bratislava?“* AI sebavedomo odpovie: **„Bratislava má približne 2,3 milióna obyvateľov.“**
> **Čo spravíš?**
> - A) Použijem číslo, AI to vie. *(0 b — slepé preberanie)*
> - B) Číslo mi príde privysoké, overím v inom zdroji. ✅ *(2 b — verifikácia; údaj je halucinácia, reálne ~475 tis.)*
> - C) Spýtam sa AI, odkiaľ to má. *(1 b — čiastočná verifikácia)*
> - D) Odmietnem a vypočítam/nájdem sám. *(2 b)*
>
> **Meria:** sklon overovať nepravdepodobné tvrdenie. *Pasca: číslo je nápadne nesprávne — kto „uverí“, je offloader.*

### Typ 2 — Hodnotenie dôveryhodnosti zdroja · Cornell/Watson-Glaser, Halpern dim 2
> **Situácia:** AI tvrdí, že „pitie kávy zvyšuje IQ o 15 bodov“ a ponúka 3 zdroje. Ktorý je najdôveryhodnejší?
> - A) Blog „SuperZdravie.sk“ s množstvom reklám. *(0 b)*
> - B) Recenzovaná štúdia v *Journal of Nutrition*, N=2000. ✅ *(2 b)*
> - C) Príspevok influencera na Instagrame. *(0 b)*
> - D) Komentár pod videom. *(0 b)*
>
> **Meria:** rozlíšenie kvality zdroja.

### Typ 3 — Detekcia halucinácie / faktickej chyby · verifikácia, kritické čítanie
> **Situácia:** AI napíše plynulý odsek o 2. svetovej vojne. Jedna veta je nepravdivá. Ktorá?
> - A) „Vojna sa začala v roku 1939.“ *(správne)*
> - B) „Slovensko bolo v tom čase samostatný štát.“ *(správne)*
> - C) „Vojna sa skončila atómovým útokom na Berlín.“ ✅ *(toto je chyba — Hirošima/Nagasaki, nie Berlín; 2 b za označenie)*
> - D) „USA vstúpili do vojny po útoku na Pearl Harbor.“ *(správne)*
>
> **Meria:** schopnosť nájsť chybu v plynulom, sebavedomom texte (najnebezpečnejší typ halucinácie).

### Typ 4 — Pravdepodobnostné uvažovanie / base rate · Halpern dim 4, CRT
> **Situácia:** AI: *„Test na chorobu je 99 % presný. Test ti vyšiel pozitívny. Chorobu má 1 z 10 000 ľudí.“* Aká je približne pravdepodobnosť, že si naozaj chorý?
> - A) 99 %. *(0 b — typický omyl, ignoruje base rate)*
> - B) Okolo 1 %. ✅ *(2 b — správne zohľadňuje nízku prevalenciu)*
> - C) 50 %. *(0 b)*
> - D) Neviem to posúdiť bez ďalších čísel — doplním si výpočet. *(1 b — metakognitívne poctivé)*
>
> **Meria:** odolnosť voči zanedbaniu základnej miery; či žiak slepo prevezme „99 %“.

### Typ 5 — Formulácia dopytu (prompt) · Lee „formulate query“, AI literacy
> **Situácia:** Máš napísať esej o klimatickej zmene. Ktorý prompt ti dá najužitočnejší *odrazový* materiál (nie hotovú esej na odpísanie)?
> - A) „Napíš mi esej o klimatickej zmene na 500 slov.“ *(0 b — offloading celej úlohy)*
> - B) „Daj mi 5 protiargumentov ku klimatickej zmene a ku každému zdroj, nech ich viem posúdiť.“ ✅ *(2 b — AI ako partner, nie ghostwriter)*
> - C) „Aké je správne riešenie klímy?“ *(0 b — vágne)*
> - D) „Sprav mi celý projekt.“ *(0 b)*
>
> **Meria:** či žiak používa AI na myslenie alebo na obídenie myslenia.

### Typ 6 — Integrácia a etika výstupu · Lee „integrate“, AI literacy etika
> **Situácia:** AI ti vygenerovala dobrý odsek. Čo s ním?
> - A) Skopírujem ho 1:1 do projektu. *(0 b — bez integrácie, etické riziko)*
> - B) Prečítam, overím fakty, prepíšem vlastnými slovami a uvediem, že som použil AI. ✅ *(2 b)*
> - C) Skopírujem, ale zmením pár slov, nech to neodhalia. *(0 b — nečestné)*
> - D) Použijem ako inšpiráciu a napíšem vlastný, lepší odsek. *(2 b)*
>
> **Meria:** integráciu výstupu + akademickú integritu.

> **Ďalšie typy do banky:** testovanie hypotéz (Halpern dim 3 — „aký ďalší údaj by najlepšie overil toto tvrdenie?“), rozpoznanie predpokladu (Watson-Glaser), rozlíšenie korelácie a kauzality. Cieľ: **banka ~40–60 položiek**, z nej náhodný/adaptívny výber 12–15 na sedenie + ekvivalentná forma pre post-test.

---

## 5. Skórovací model (ako z volieb vznikne „profil schopností“)

Každá položka prispieva 0–2 body do **jednej hlavnej dimenzie**. Dimenzie (mapované na SOTA):

| Dimenzia v hre | Zdroj/teória | Príklad typu |
|---|---|---|
| **Verifikácia / odolnosť voči offloadingu** | Gerlich, Lee „evaluate“ | Typ 1, 3 |
| **Hodnotenie zdrojov a argumentov** | Halpern dim 2, Watson-Glaser | Typ 2 |
| **Pravdepodobnostné uvažovanie** | Halpern dim 4, CRT | Typ 4 |
| **Efektívne použitie AI (prompting)** | Lee „formulate“, AI literacy | Typ 5 |
| **Integrácia a etika** | Lee „integrate“, AI literacy etika | Typ 6 |
| **Testovanie hypotéz** | Halpern dim 3 | (doplnkový typ) |

**Výstupné metriky na žiaka:**
- skóre po dimenziách (0–100 % v každej),
- **celkový index kritického narábania s AI** (vážený priemer),
- **offloading index** = % uzlov, kde žiak slepo prevzal AI odpoveď (najmä keď bola nesprávna),
- **behaviorálne:** medián času rozhodnutia, počet použitých nápovied, počet „odovzdaní úlohy AI“.

**Prečo je to skvelé na interpretáciu (Dokument 3):** tieto čísla idú priamo do ANCOVA / korelácií / zhlukov. Žiak = vektor čísel namiesto kopy textu.

---

## 6. Ako sa hra napája na 3-skupinový experiment

| Skupina | AI vrstva v hre | Čo simuluje |
|---|---|---|
| **Adaptívna** | Reálny LLM, mení obtiažnosť/ústretovosť podľa výkonu; sokratické nápovedy | Khanmigo, pedagogický nástroj (Kestin) |
| **Generická** | Statický „ChatGPT“ — vždy odpovie priamo, vrátane občasných halucinácií | holý ChatGPT |
| **Kontrolná** | Žiadna AI nápoveda — len uzly a vlastný úsudok | tradičné riešenie |

Meracie uzly sú vo všetkých troch identické → **porovnateľnosť**. Líši sa len to, akú pomoc žiak dostáva → **to je manipulovaná premenná.**

---

## 7. Čo povedať školiteľovi (zhrnutie)

> **„Navrhujem hru ‚AI Detektív‘: žiak rieši prípady s pomocou AI, ktorá zámerne občas klame — halucinuje, používa nedôveryhodné zdroje, robí logické chyby. Pri každom kroku sa žiak rozhoduje z uzavretých možností (uver/over/spýtaj sa na zdroj/odmietni), čím priamo a objektívne meriame kritické narábanie s AI. Každá voľba mapuje na dimenziu (Halpern + Lee + offloading) a skóruje sa automaticky — tým riešim problém, že otvorené prompty sa ťažko kvantifikujú. Hra má tri režimy, ktoré sú zároveň tromi experimentálnymi skupinami: adaptívna AI, generická AI a kontrola bez AI. Mám funkčné demo v prehliadači, ktoré zbiera voľby, časy a exportuje JSON na analýzu.“**

---

## 8. Odkaz na implementáciu
Spustiteľné demo: **`podklady/hra-demo/index.html`** (otvor v prehliadači, netreba inštaláciu ani internet). Obsahuje 6 typov otázok vyššie, automatické skórovanie, behaviorálne logovanie a export JSON. Detaily v hlavičke súboru a v `podklady/hra-demo/README.md`.

---

## Zdroje
- Mapovanie na dimenzie kritického myslenia: Halpern CTA (Dokument 1), Lee et al. CHI 2025 (6 aspektov kognitívneho úsilia), Gerlich (offloading).
- Forced-choice meranie kritického myslenia: [HCTA formát](https://psycnet.apa.org/doiLanding?doi=10.1037%2Ft10940-000), [Cornell/CRT](https://philosophy.hku.hk/think/critical/tests.php).
- AI literacy dimenzie (povedomie/použitie/hodnotenie/etika): [Ng 2024 BJET](https://bera-journals.onlinelibrary.wiley.com/doi/10.1111/bjet.13411).
- Adaptívny sokratický dizajn ako vzor: Slijepcevic & Yaylali (Khanmigo), Kestin (Harvard) — tvoja SOTA.

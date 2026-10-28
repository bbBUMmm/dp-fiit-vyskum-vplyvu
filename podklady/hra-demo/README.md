# AI Detektív — demo meracieho nástroja

Spustiteľné demo hry z **Dokumentu 4**. Meria kritické narábanie s AI cez uzavreté voľby a exportuje dáta na štatistickú analýzu.

## Ako spustiť
**Dvojklik na `index.html`** → otvorí sa v prehliadači. Žiadna inštalácia, žiadny internet, žiadny build. Funguje offline (Firefox/Chrome/Safari).

## Čo demo robí
1. Žiak zadá pseudonym a vyberie režim (= experimentálna skupina).
2. Rieši 12 „uzlov" — situácií, kde AI asistent niečo tvrdí (a **občas klame**).
3. Pri každom uzle volí z 3–4 uzavretých možností → okamžitá spätná väzba + skóre.
4. Na konci dostane **profil po dimenziách** (radarový graf + bary), **offloading index**, behaviorálne ukazovatele a **export JSON**.

## Tri režimy = tri experimentálne skupiny
| Režim | AI vrstva | Vzor zo SOTA |
|---|---|---|
| Adaptívna AI | prispôsobuje obtiažnosť + sokratické nápovedy | Khanmigo (Slijepcevic), Kestin |
| Generická AI | statické odpovede vrátane chýb | holý ChatGPT |
| Bez asistencie | žiadne nápovedy/adaptácia | kontrolná skupina |

**Meracie uzly (otázky + skórovanie) sú vo všetkých režimoch identické** → výsledky sú porovnateľné. Líši sa len poskytnutá pomoc = manipulovaná premenná.

## Súbory
- `index.html` — štruktúra + štýl + obrazovky (štart / hra / výsledky)
- `banka.js` — **merací nástroj**: banka 14 úloh v 6 dimenziách (toto výskumník rozširuje a validuje)
- `hra.js` — engine: stav, adaptivita, skórovanie, radar, export
- `test.js` — kontrola integrity banky + simulácia skórovania (`node test.js`)

## Čo sa zaznamenáva (export JSON)
```jsonc
{
  "studentId": "ZK-014", "mode": "adaptivny", "timestamp": "...",
  "overallPct": 75,                       // celkový index kritického narábania s AI
  "dimPct": { "verifikacia": 80, ... },   // skóre v každej dimenzii (0-100 %)
  "offloadingIdx": 17,                    // % uzlov so slepým prebratím AI
  "relianceOnWrong": 1,                   // koľkokrát prebral NESPRÁVNU AI odpoveď
  "behaviour": { "medianTimeMs": 8400, "hintsTotal": 2 },
  "responses": [ /* záznam každého uzla: voľba, skóre, čas, nápovedy */ ]
}
```
Jeden JSON = jeden riadok dátovej matice → priamo do R/jamovi/SPSS (Dokument 3).

## 6 typov otázok (mapovanie na dimenzie)
1. **Kalibrácia dôvery** → verifikácia / offloading
2. **Hodnotenie zdroja/argumentu** → zdroje (Halpern dim 2, Watson-Glaser)
3. **Detekcia halucinácie** → verifikácia (kritické čítanie)
4. **Pravdepodobnostné uvažovanie** → base-rate, CRT (Halpern dim 4)
5. **Formulácia promptu** → efektívne použitie AI (Lee „formulate", AI literacy)
6. **Integrácia a etika** → integrácia výstupu + akademická integrita
7. *(doplnkový)* **Testovanie hypotéz** → Halpern dim 3, korelácia vs. kauzalita

## Validácia pred ostrým nasadením (TODO pre prácu)
- Pilot ~30 žiakov → položková analýza, vnútorná konzistencia (Cronbach α), obtiažnosť a diskriminačná sila položiek.
- Vytvoriť **ekvivalentnú formu B** banky pre post-test (rovnaká štruktúra, iné konkrétne prípady).
- Vyvážiť pomer „AI správne / AI nesprávne" tak, aby sa hra nedala prejsť stratégiou „vždy ver" ani „vždy odmietni" (aktuálne 4:6).

## Voliteľné: napojenie na reálny LLM (adaptívny režim v ostrej verzii)
Demo používa „mock AI" z lokálnej banky (preto funguje offline a je reprodukovateľné).
Pre ostrý adaptívny režim stačí v `hra.js` nahradiť statické `item.aiSays` volaním na LLM API
(napr. cez `fetch` na backend, ktorý drží API kľúč — nikdy nie v prehliadači).
**Meracie uzly nechaj nezmenené**, mení sa len zdroj `aiSays` a sokratických nápovied —
tým ostane zachovaná porovnateľnosť so SOTA aj reprodukovateľnosť.

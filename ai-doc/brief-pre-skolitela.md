# Čo je hotové — podklad na konzultáciu

*Stav k 2. októbru 2026. 198 strán, 479 automatických testov, 166 konzistenčných
kontrol, 504 generovaných hodnôt, 104 bibliografických položiek.*

---

## 1. Ak máte minútu

Práca má dva prepojené prínosy a jeden stav.

**Prínos 1 — merací nástroj.** Index epistemickej kvality promptov (PEQI) mení
mieru kognitívneho offloadingu zo *sebahodnotenej* veličiny na *pozorovanú*:
počíta sa automaticky z promptov, ktoré žiak skutočne odoslal. Doteraz sa merala
dotazníkom (Gerlich 2025) alebo EEG (Kosmyna 2025) — prvé je pri správaní, ktoré
žiak nemá dôvod priznať, systematicky skreslené, druhé je v triede nepoužiteľné.

**Prínos 2 — dizajn, ktorý oddeľuje pedagogiku od modelu.** Doterajšie
porovnania adaptívnych a generických nástrojov zamieňajú model, rozhranie, obsah
aj pedagogiku, takže rozdiel nemožno pripísať žiadnemu z nich. Tu je rovnaký
model, rovnaké úlohy, rovnaké rozhranie, rovnaký učiteľ — mení sa výhradne
pedagogická vrstva. A nie je to tvrdenie v metodike: všetky tri podmienky beží
jeden program a test to overuje.

**Stav.** Dizajn je kompletný, nástroj implementovaný a nasadeniaschopný,
analytický plán uzavretý a overený na simulovaných dátach. **Zber v školách
zatiaľ neprebehol** — to je ďalší krok a je to jediná časť zadania, ktorá
zostáva otvorená.

---

## 2. Mapovanie na zadanie

Toto je tabuľka, ktorú školiteľ pravdepodobne chce vidieť ako prvú.

| Bod zadania | Stav | Kde v práci |
|---|---|---|
| Analýza súčasného nasadzovania UI v školách | **hotové** | §4 `sec:nasadenie` |
| Kvantitatívne vyhodnotenie posudzovaných riešení | **hotové** | tab. `tab:nasadenia` |
| Kvalitatívne vyhodnotenie | **hotové** | §4, tri pozorovania z nasadenia |
| Identifikácia prínosov a obmedzujúcich faktorov | **hotové** | tab. `tab:prinosy-obmedzenia` |
| Návrh riešenia: systematický zber údajov | **hotové** | §5 `sec:infrastruktura`, kap. 7 |
| Návrh riešenia: **kategorizácia používateľov** | **hotové** | §5 `sec:kategorizacia` |
| Návrh riešenia: meranie zmien v schopnostiach pred/po | **hotové** | §5 `sec:tri-vrstvy`, `sec:konstrukty` |
| Implementácia riešenia | **hotové** | kap. 7, 4 komponenty, 479 testov |
| **Overenie použitím v školskom prostredí** | **otvorené** | pripravené: `build-school-kit.ps1`, príloha F |
| Analýza zozbieraných dát | **plán uzavretý, dáta chýbajú** | kap. 6 (zatiaľ simulované) |
| Porovnanie s dostupnými riešeniami | **hotové** | kap. 7 `sec:porovnanie` |
| Formulácia odporúčaní | **hotové** | kap. 7 `sec:odporucania`, 14 odporúčaní |
| Teoretické východiská a výskum **na Slovensku** | **hotové** | §4 `sec:slovensko` |
| Dopady na žiakov **či učiteľov** | **hotové** (oboje) | §5 `sec:ucitelia` |
| Povinná literatúra: Garzón et al. 2025 | citované | §3, §4 |
| Povinná literatúra: Discover Education 2025 | citované | §4 `sec:slovensko` |

Automatická kontrola (`check_assignment_compliance`, 16 tvrdení) zlyhá pri
preklade, ak sa ktorákoľvek z týchto častí z práce stratí.

---

## 3. Čo je na práci nové

Ak sa školiteľ spýta „čo je tu vlastne váš prínos“, toto je poradie, v akom to
má zmysel povedať.

**1. PEQI.** Taxonómia žiackych dopytov ukotvená v rámci ICAP, so šiestimi
úrovňami od „napíš mi kód“ po „myslím si X, lebo Y — kde robím chybu?“.
Automatický klasifikátor na priehľadných lexikálnych príznakoch (nie neprieh­ľadný
model, aby škola aj oponent vedeli overiť *prečo* bol prompt zaradený tak, ako
bol) dosahuje na 90 ručne kódovaných slovenských promptoch zhodu κ = 0,99.

**2. Diferenciálna chyba merania mediátora.** Toto je časť, ktorá je
publikovateľná samostatne. Mediátor nie je pozorovaný, ale *odhadnutý*
klasifikátorom — a chyba toho odhadu môže závisieť od podmienky, ktorú dizajn
randomizuje. Tri tvrdenia, odvodené aj overené simuláciou:

- redukovaná forma je voči chybe merania mediátora **úplne odolná**;
- diferenciálna chyba nafúkne prvý stupeň, a tým inštrumentálny odhad **zmenší**
  (opak bežnej intuície);
- mediačný odhad je najprv nafúknutý a potom utlmený tak, že sa obe skreslenia
  môžu **presne vyrušiť** — odhad potom vyzerá bezchybne, hoci každý koeficient
  v ňom je nesprávny.

**3. Kategorizácia používateľov ako zistenie, nie ako tabuľka.** Na simulovaných
dátach je celkový účinok generického nástroja −0,06 a od nuly nerozlíšiteľný,
kým profil „slepo dôverujúci“ stráca −0,53. **Priemer triedy hovorí „žiadny
účinok“ o populácii, v ktorej bola časť žiakov preukázateľne poškodená.**

**4. Rozlíšenie toho, čo dizajn preukazuje, od toho, čo predpokladá.**
Randomizácia prideľuje *podmienku*, nie *kvalitu promptov*. Mediačné tvrdenie
teda stojí na predpoklade, ktorý dizajn nedodáva. Do konfirmačnej rodiny preto
vstupujú len tri tvrdenia, ktoré sú randomizáciou identifikované; mechanizmus sa
testuje trianguláciou troch odhadov pod tromi rôznymi predpokladmi plus
analýzou citlivosti.

**5. Reprodukovateľnosť ako vlastnosť, nie ako disciplína.** Žiadne číslo v
kapitolách 5 a 6 nie je napísané rukou; všetkých 504 vzniká generovaním. To
isté platí pre čísla, ktoré práca uvádza o sebe samej.

---

## 4. Argument, ktorý prácu drží pohromade

Ak má školiteľ počuť jednu myšlienku, je to táto.

Empirické zistenia o vplyve UI na učenie si **zdanlivo protirečia**: adaptívny
tútor prekonáva aktívne učenie (Kestin 2025), generatívny nástroj znižuje
výsledky o 17 % (Bastani 2025), priame porovnanie adaptívneho a generického
nenachádza rozdiel (Slijepčević 2025).

Práca tvrdí, že rozpor je zdanlivý, a vysvetľuje ho jedno rozlíšenie a jedna
hypotéza:

- **Rozlíšenie:** „výsledky vzdelávania“ nie sú jedna veličina, ale tri — výkon
  počas hodiny, okamžité vybavenie, a trvalé vybavenie s transferom. Tieto tri
  sa môžu usporiadať v **opačnom poradí**.
- **Hypotéza:** nástroj zvyšuje prvé dve takmer vždy, pretože odstraňuje úsilie.
  Jeho vplyv na tretiu závisí od toho, či interakcia zostala *generatívna*, alebo
  sa stala *offloadingová*.

A tá veličina — charakter interakcie — doteraz nebola priamo meraná. Preto PEQI.
Preto dizajn. V tomto poradí.

---

## 5. Čo bolo overené a ako

Toto je argument, ktorý robí z práce metodologickú, nie len technickú.

Analytický plán bol **implementovaný a spustený na dátach zo známeho
generujúceho modelu pred zberom**. Postup odhalil deväť chýb návrhu, ktoré by sa
inak prejavili až po zbere, keď je náprava nemožná. Napríklad:

- singularita v kódovaní prenosu medzi periódami (model vracal nekonečné chyby);
- chýbajúce prepojenie testových foriem kotviacimi položkami — rozdiel medzi
  okamžitým a odloženým skóre by zamieňal zabúdanie s obtiažnosťou testu;
- prítomnosť neidentifikovateľnej hypotézy v konfirmačnej rodine;
- klasifikátor sa dal oklamať štvorslovnou formulkou — a to **systematicky v
  prospech jednej podmienky**, lebo adaptívna vrstva takú formulku od žiakov
  vyžaduje;
- dve implementácie tej istej taxonómie sa ticho rozišli.

Za zmienku stojí, **ako** sa chyby našli, lebo to neboli tri rovnaké postupy:
spustením plánu na dátach so známou odpoveďou; písaním o tom, čo kód robí; a
pokusom o zneužitie vlastného nástroja. Tretí bol najproduktívnejší a v
metodických prácach sa vyskytuje najzriedkavejšie.

---

## 6. Čo chýba — povedané priamo

Toto treba povedať samo, skôr než sa na to školiteľ spýta.

| Chýba | Prečo | Dôsledok |
|---|---|---|
| **Zber v školách** | ešte neprebehol | kap. 6 obsahuje simulované dáta; bod zadania „overte použitím v školskom prostredí“ zostáva otvorený |
| **Redakčná revízia textu** | nezačatá | kap. 5 má 1007 riadkov a pravdepodobne obsahuje prekryv medzi `sec:konstrukty` a `sec:tri-vrstvy` |
| Pilot testu kritického myslenia | 12 položiek napísaných, neoverených | príloha G je návrh nástroja, nie validovaný nástroj |
| Prístup k FCI | vyžaduje overený účet na PhysPort | fyzikálne rameno zatiaľ nemožno pripraviť |
| Súhlas s použitím úloh iBobor | nevyžiadaný | FMFI UK |
| Etické schválenie | nevyžiadané | kritická cesta celého projektu |
| Overenie autorstva jednej citácie | `hariyanto2025adaptive` | zadanie uvádza „Smith, A.; Johnson, B.“, nájdený článok uvádza iných autorov — **treba overiť pred odovzdaním** |

---

## 7. Čo potrebujem od školiteľa

Konkrétne otázky, s ktorými má zmysel prísť:

1. **Školy.** Máte kontakt na gymnázium alebo SOŠ ochotné uvoľniť tri hodiny
   informatiky? Toto je jediná vec, ktorá blokuje bod zadania o overení
   použitím.
2. **Etická komisia.** Aký je postup a aký je realistický čas na schválenie?
   Je na kritickej ceste.
3. **Rozsah.** Pilot (1–2 triedy) alebo plná štúdia (18 tried)? Plná vyžaduje
   nábor začínajúci teraz.
4. **Citácia.** Zadanie uvádza Smith & Johnson; DOI vedie na článok s iným
   autorstvom. Ktorý je správny?
5. **Fyzikálne rameno.** Má zmysel ho udržať, keď je fyzika na SOŠ slabo
   zastúpená a interakcia *predmet × podmienka* bude čiastočne zamenená s typom
   školy?

---

## 8. Čo školiteľovi naozaj ukázať

Testy sa neukazujú. Nikto si neprečíta 480 názvov testov a nie je to obsah
práce — je to lešenie. Z testov sa nepoužíva výstup, ale jediná veta, ktorá sa
vďaka nim dá povedať na obhajobe bez rizika:

> „Žiadne číslo v kapitolách 5 a 6 nie je napísané rukou. Všetkých 504 vzniká
> generovaním z kódu. Keď sa zmení parameter a reťazec sa znova spustí, práca sa
> aktualizuje sama.“

To je odpoveď na otázku oponenta „ako viete, že tie čísla sedia“. Nič viac z
testov netreba.

### Ukážka, ktorá trvá dve minúty a ktorú si školiteľ zapamätá

Spustite dve inštancie vedľa seba a položte obom **tú istú otázku**:

```powershell
# okno 1 -- generický nástroj
cd D:\MastersFIIT\exercise-client
python server.py --condition G --session demo --salt x --provider stub --port 5311

# okno 2 -- adaptívny nástroj
python server.py --condition A --session demo --salt x --provider stub --port 5312
```

Otázka: **„napíš mi celé riešenie“**

| Podmienka | Odpoveď |
|---|---|
| **G** | „Binárne vyhľadávanie funguje tak, že porovná stredný prvok a podľa výsledku zahodí polovicu intervalu.“ |
| **A** | „Hotové riešenie ti nedám. Povedz mi radšej, ktorý krok ti nesedí, a pôjdeme od neho.“ |

Rovnaký model, rovnaké úlohy, rovnaké rozhranie, rovnaký kód. Líši sa výhradne
pedagogická vrstva. **Toto je celá manipulácia, viditeľná za tridsať sekúnd** — a
je to presne to, čo doterajšie porovnania adaptívnych a generických nástrojov
nedokážu oddeliť.

Ak je čas, pridajte podmienku K: server odmietne asistenta chybou 403 a zapíše
to ako odchýlku od protokolu. Odmietnutie je na serveri, nie v rozhraní, takže
ho žiak nemôže obísť.

### Čo ukázať z práce samotnej

Tri miesta v PDF, v tomto poradí:

1. **§4 „Syntéza: zjednocujúca hypotéza“** — prečo si literatúra protirečí a ako
   to jedno rozlíšenie vysvetľuje. Toto je myšlienka práce.
2. **Tabuľka taxonómie PEQI** (príloha B) — prínos na jednej strane, so
   skutočnými slovenskými promptmi.
3. **§6 „Čo simulácia odhalila“** — deväť chýb návrhu nájdených *pred* zberom.
   Toto je najsilnejšia časť: nie že je dizajn dômyselný, ale že bol napadnutý
   skôr, než sa použil.

A nakoniec priečinok `school-kit\`, lebo zadanie žiada nasaditeľnosť a priečinok
je konkrétny.

### Čo povedať o nájdených chybách

Nie obranne. Deväť chýb nájdených pred zberom je **výsledok**, nie priznanie —
každá z nich by sa inak prejavila až po zbere, keď je náprava nemožná. Dve z
nich boli v mojej vlastnej práci: klasifikátor sa dal oklamať štvorslovnou
formulkou, a to systematicky v prospech jednej podmienky; a dve implementácie
tej istej taxonómie sa ticho rozišli.

Posledná z nich sa našla deň pred touto konzultáciou a stojí za zmienku, lebo
ukazuje hranice testovania: server padal pri štarte vždy, keď jeho výstup nešiel
do konzoly s UTF-8 — teda na bežnom školskom notebooku. Hodina by sa skončila
skôr, než by sa začala. Testy to nezachytili, pretože ich spúšťač nastavoval
premennú prostredia, ktorá chybu zakrývala. **Testovacie prostredie maskovalo
chybu, ktorú malo nájsť.** Opravené a doplnené o test, ktorý tú premennú
výslovne odstraňuje.

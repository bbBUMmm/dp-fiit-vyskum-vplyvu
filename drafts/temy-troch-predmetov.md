# Tri predmety, jedna téma v každom

*Návrh na integráciu do kapitoly 5, časť „Učivo, témy a ich výber" (`sec:temy`)
a „Druhý predmet: fyzika" (`sec:fyzika`). Stav k 16. 10. 2026. Nič z tohto
textu zatiaľ nie je v LaTeX-e.*

---

## 1. Rozhodnutie

| Predmet | Téma | Ročník |
|---|---|---|
| **Informatika** | Vyhľadávanie v poli: lineárne verzus binárne | 2.–3. |
| **Matematika** | Zložené úrokovanie a exponenciálny rast | 2.–3. |
| **Fyzika** | Jednosmerný prúd: sériové a paralelné zapojenie | 2.–3. |

Cieľová populácia: gymnázium a technická SOŠ (elektrotechnika, IT), 2. alebo 3.
ročník. Štvrtý ročník sa vynecháva: je to maturitný ročník, školy v ňom hodiny
neuvoľňujú a témy sú už prebraté.

Každá trieda absolvuje všetky tri predmety, každý v inej podmienke (K, G, A).
Pokus nahrádza bežnú hodinu, na ktorej sa podľa školského vzdelávacieho programu
daná téma v tom termíne preberá. Škola tak nestráca vyučovací čas, čo je
najsilnejší argument pri nábore.

---

## 2. Prečo práve tieto tri: spoločná štruktúra

Krížový dizajn porovnáva podmienky u toho istého žiaka na rôznom učive. Funguje
len vtedy, keď sú témy porovnateľné. Doteraz to zaručovali tri témy z jedného
predmetu. Pri troch predmetoch to musí zaručiť **spoločná štruktúra tém**.

Všetky tri sú postavené rovnako: **intuitívny lineárny alebo sčítací model,
ktorý zlyháva, oproti správnemu modelu**; prečo zlyháva; a kedy jednoduchší
postup stačí.

| | Intuícia, ktorá zlyháva | Správny model | Typická chyba žiaka |
|---|---|---|---|
| **I** | dvojnásobné pole = dvojnásobok krokov | logaritmický rast: +1 krok | lineárna extrapolácia |
| **M** | dvojnásobná doba = dvojnásobný úrok | exponenciálny rast | linearizácia exponenciály |
| **F** | ďalší rezistor = väčší odpor; prúd sa „míňa" | paralelne odpor klesá; prúd sa zachováva | sčítacia a lokálna úvaha |

Z toho plynú tri veci, na ktorých dizajn stojí:

- **Jedna špecifikačná tabuľka pre všetky tri predmety** (2/2/4/3/1 položiek
  podľa kognitívnej úrovne). Rozptyľovače v každom predmete diagnostikujú tú
  istú triedu chyby: lineárnu alebo sčítaciu intuíciu.
- **Generatívny nástroj každú úlohu vyrieši celú.** To je podmienka, aby sa
  manipulácia vôbec uskutočnila: pri úlohe, ktorú nástroj nevyrieši, nie je čo
  odovzdať.
- **Téma priamo zasahuje hypotézu práce.** Nástroj, ktorý vydá výsledok,
  žiakovi umožní obísť práve ten moment, keď by si všimol, že jeho intuícia
  nesedí. Ak offloading škodí, prejaví sa to tu.

---

## 3. Témy

### Informatika: vyhľadávanie v poli

Ponecháva sa doterajšia téma T1. Je jediná úplne pripravená: scenár hodiny,
osem úloh, úlohy v cvičnom klientovi, obe testové formy v zásobníku.

**Zisk navyše:** témy T2 (triedenie) a T3 (rekurzia) dnes existujú len ako
skrátené opisy. Pri troch predmetoch ich netreba dopisovať.

### Matematika: zložené úrokovanie a exponenciálny rast

**Ukotvenie v ŠVP.** Inovovaný ŠVP pre gymnázium obsahuje v obsahovom štandarde
„úrok, (ročná) úroková miera, jednoduché a zložené úrokovanie" a vo výkonovom
štandarde „riešiť jednoduché úlohy na pravidelné vkladanie alebo vyberanie súm
z banky", „vysvetliť princíp splácania pôžičky" a „porovnať výhodnosť dvoch
pôžičiek". Na inom mieste: vysvetliť, ako z opisu exponenciálneho rastu „za
rovnaký čas sa hodnota zväčší vždy o rovnaký počet percent" vyplýva predpis
exponenciálnej funkcie. Je to teda jadro, ktoré má každý žiak gymnázia.

*Zvážená a zamietnutá alternatíva:* aritmetická a geometrická postupnosť. Je
v cieľových požiadavkách na maturitu, ale ŠVP ju uvádza medzi témami, ktoré
„nie sú náplňou Štátneho vzdelávacieho programu" alebo v ňom nie sú spracované
do dostatočnej hĺbky. Nie každá trieda by ju mala.

**Obsah bloku.**
- *Výklad (22 min):* jednoduché verzus zložené úrokovanie; výpočet rok po roku
  verzus vzorec K_n = K_0 · (1 + p)^n; prečo dvojnásobná doba prinesie viac než
  dvojnásobný úrok; pravidlo 72 ako odhad doby zdvojnásobenia; kedy vzorec
  nestačí (vklady v rôznych termínoch, treba počítať rok po roku).
- *Úlohy (32 min):* výpočet rok po roku; použitie vzorca; porovnanie
  jednoduchého a zloženého úročenia; nájdenie chyby v „lineárnom" výpočte;
  doba zdvojnásobenia; pravidelný vklad; výber výhodnejšej z dvoch pôžičiek;
  posúdenie tvrdenia „za 20 rokov dostanem dvakrát viac úrokov ako za 10".

**Prečo práve táto téma.** Linearizácia exponenciály je dobre doložená
systematická chyba: Stango a Zinman (2009) ju nazývajú *exponential growth
bias* a ukazujú, že domácnosti s ňou si viac požičiavajú a menej sporia. Téma
má teda praktický dosah mimo školy, a súvisí s finančnou gramotnosťou.

**Test.** Vlastný, 12 položiek podľa spoločnej špecifikačnej tabuľky. Na túto
tému neexistuje overený slovenský inventár; postup je rovnaký ako pri
informatike.

### Fyzika: jednosmerný prúd, sériové a paralelné zapojenie

**Ukotvenie v ŠVP.** Inovovaný ŠVP fyziky pre gymnázium obsahuje „elektrický
prúd v kovoch, elektrolytoch a v plynoch", „elektrický odpor", „Ohmov zákon",
„V-A charakteristiku vláknovej žiarovky" a „elektrický výkon spotrebiča".
V technických SOŠ je téma základom odborných predmetov.

**Obsah bloku.**
- *Výklad (22 min):* prúd sa v obvode nespotrebúva; napätie a Ohmov zákon;
  sériové verzus paralelné zapojenie; prečo pridanie rezistora paralelne
  celkový odpor zníži; postup „uzol po uzle" verzus zjednodušenie na náhradný
  odpor; kedy zjednodušenie nejde (mostíkové zapojenie).
- *Úlohy (32 min):* poradie jasu žiaroviek v obvode; výpočet prúdu a napätia;
  náhradný odpor; nájdenie chyby v úvahe „prúd sa cestou míňa"; čo sa stane
  s ostatnými žiarovkami, keď jedna vyhorí (séria verzus paralel); voľba
  zapojenia pre konkrétne použitie.

**Prečo práve táto téma.** Miskoncepcie o obvodoch sú dobre zmapované a
pretrvávajú aj po výučbe; hlavným zdrojom je podľa Engelhardtovej a Beichnera
(2004) nejasná predstava o tom, čo je prúd. Rozptyľovače sa teda dajú písať
podľa doložených chýb, nie naslepo.

**Test.** Vlastný, 12 položiek podľa spoločnej špecifikačnej tabuľky,
s rozptyľovačmi podľa chýb z DIRECT. Samotný DIRECT ako výstup nevyhovuje
z dvoch dôvodov: trvá 30 minút a do 16-minútového okna okamžitého testu sa
nevojde; a **slovenský ani český preklad neexistuje** (PhysPort uvádza čínsky,
fínsky, nemecký, grécky, španielsky a švédsky). Môže slúžiť ako externé
kritérium validity v pilote, po preklade.

**Čo sa tým mení oproti terajšej práci.** Doterajší návrh používal FCI
(mechanika), lebo má slovenský preklad. Mechanika sa však zvyčajne preberá na
začiatku štúdia, takže v 2. a 3. ročníku by nešlo o nové učivo, a nový návrh
s ňou preto nepočíta. Časť `sec:fyzika` treba prepísať.

---

## 4. Čo to mení na dizajne

1. **Krížový dizajn zostáva.** Namiesto troch tém sa striedajú tri predmety a
   šesť sekvencií vyvažuje predmet voči podmienke. Predmet vstupuje do modelu
   ako fixný efekt, tak ako predtým téma.
2. **Rôzni učitelia: nové riziko.** Doteraz učil všetky tri podmienky jeden
   učiteľ, a bola to súčasť kontroly. Teraz má každý predmet svojho učiteľa.
   Učiteľ sa so podmienkou nezamieňa, lebo predmet je voči nej vyvážený, ale
   vzniká možná interakcia *učiteľ × podmienka*: učiteľ, ktorému nástroj sedí,
   ho využije lepšie. Všetci traja učitelia musia mať rovnaké zaškolenie a
   rovnaký scenár, a interakcia sa vykazuje.
3. **Nábor sa zužuje.** Trieda musí mať v tom istom polroku všetky tri
   predmety, prakticky teda gymnázium a technická SOŠ. Obchodné akadémie a
   väčšina netechnických SOŠ vypadnú, lebo nemajú fyziku alebo programovanie.
4. **Porovnávať sa dá len v rámci predmetu.** Testy majú spoločnú štruktúru,
   nie obsah. Kontrast podmienok sa odhaduje v rámci predmetu. Úroveň vedomostí
   medzi predmetmi porovnávať nemožno.
5. **Nástroj treba doplniť.** Zásobník potrebuje banky pre matematiku a fyziku
   (štyri: dve formy na predmet). Cvičný klient potrebuje úlohy pre oba predmety.
   Systémový prompt podmienky A je napísaný pre informatiku a treba ho
   zovšeobecniť.
6. **Zisk.** Interakcia *predmet × podmienka* je odhadnuteľná priamo u tých
   istých žiakov, a nie len cez paralelné rameno v iných triedach. Tvrdenie
   práce sa tak týka troch predmetov, nie jedného.

---

## 5. Čo treba overiť pred integráciou

- [ ] **Ročník v ŠkVP konkrétnej školy.** ŠVP určuje obsah, nie ročník; ten si
      škola stanovuje sama. Pre každú náborovú školu overiť, v ktorom ročníku a
      polroku sú úrokovanie a elektrický prúd.
- [ ] **Matematika na SOŠ.** Ukotvenie úrokovania je overené len pre ŠVP
      gymnázia; ŠVP pre SOŠ nebol kontrolovaný.
- [ ] **Hodinová dotácia fyziky** v 2. a 3. ročníku technických SOŠ.
- [ ] **Súhlas s prekladom DIRECT**, ak sa má použiť ako kritérium (autori,
      PhysPort).
- [ ] **Tri učitelia v jednej triede ochotní spolupracovať:** reálne náborové
      riziko, treba ho preveriť pri prvom kontakte so školou.

---

## 6. Zdroje

- Štátny pedagogický ústav. *Inovovaný ŠVP — Fyzika, gymnázium so štvorročným
  a päťročným vzdelávacím programom.*
  https://www.statpedu.sk/files/articles/dokumenty/inovovany-statny-vzdelavaci-program/fyzika_g_4_5_r.pdf
- Štátny pedagogický ústav. *Inovovaný ŠVP — Matematika, gymnázium so
  štvorročným a päťročným vzdelávacím programom.*
  https://www.statpedu.sk/files/articles/dokumenty/inovovany-statny-vzdelavaci-program/matematika_g_4_5_r.pdf
- Engelhardt, P. V., & Beichner, R. J. (2004). Students' understanding of direct
  current resistive electrical circuits. *American Journal of Physics, 72*(1),
  98–115. https://doi.org/10.1119/1.1614813
- PhysPort: DIRECT, stránka nástroja a zoznam prekladov.
  https://www.physport.org/assessments/DIRECT
- Stango, V., & Zinman, J. (2009). Exponential growth bias and household
  finance. *The Journal of Finance, 64*(6), 2807–2849.

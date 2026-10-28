/* =====================================================================
   AI DETEKTÍV — BANKA ÚLOH (merací nástroj)
   ---------------------------------------------------------------------
   Toto je "merací nástroj" práce. Každá položka = jeden rozhodovací uzol
   s uzavretými možnosťami. Výskumník túto banku rozširuje a validuje na
   pilote (Cronbach alfa, položková analýza).

   Štruktúra položky:
     id          – jedinečný kód
     type        – typ otázky (6 typov, viď Dokument 4)
     dimension   – ktorú schopnosť meria (kľúč do DIMENZIE)
     difficulty  – 1 (ľahká) .. 3 (ťažká) — používa adaptívny režim
     brief       – kontext/úloha
     aiSays      – čo tvrdí AI asistent (null = bez AI vstupu)
     aiCorrect   – či je AI tvrdenie naozaj správne (kľúč pre "pascu")
     question    – samotná otázka
     options[]   – { text, score(0-2), reliance(bool), correct(bool), feedback }
                   reliance = táto voľba znamená "slepé prebratie AI" (offloading)
   ===================================================================== */

const DIMENZIE = {
  verifikacia:   { nazov: "Verifikácia / odolnosť voči offloadingu", farba: "#4ade80" },
  zdroje:        { nazov: "Hodnotenie zdrojov a argumentov",         farba: "#60a5fa" },
  pravdepodobnost:{ nazov: "Pravdepodobnostné uvažovanie",           farba: "#f472b6" },
  prompting:     { nazov: "Efektívne použitie AI (prompting)",       farba: "#fbbf24" },
  integracia:    { nazov: "Integrácia a etika výstupu",              farba: "#a78bfa" },
  hypotezy:      { nazov: "Testovanie hypotéz",                      farba: "#22d3ee" },
};

const BANKA = [
  /* ---------- TYP 1: Kalibrácia dôvery (verifikacia) ---------- */
  {
    id: "v1", type: "Kalibrácia dôvery", dimension: "verifikacia", difficulty: 1,
    brief: "Pripravuješ referát o Slovensku. Potrebuješ počet obyvateľov Bratislavy.",
    aiSays: "Bratislava má približne 2,3 milióna obyvateľov.",
    aiCorrect: false,
    question: "Ako naložíš s touto odpoveďou?",
    options: [
      { text: "Použijem číslo, AI to predsa vie.", score: 0, reliance: true,
        feedback: "Slepé prebratie. Číslo je halucinácia — Bratislava má ~475-tisíc obyvateľov. AI znie sebavedomo aj keď sa mýli." },
      { text: "Číslo mi príde privysoké, overím ho v inom zdroji.", score: 2, correct: true,
        feedback: "Správne. 2,3 milióna je nereálne (to je skôr celé Slovensko / Paríž). Overenie odhalí halucináciu." },
      { text: "Spýtam sa AI, odkiaľ to má.", score: 1,
        feedback: "Čiastočne dobré, ale AI si zdroj môže vymyslieť tiež. Lepšie je overiť nezávisle." },
      { text: "Odmietnem a nájdem číslo v štatistickom úrade.", score: 2, correct: true,
        feedback: "Výborne — primárny zdroj je najspoľahlivejší." },
    ],
  },
  {
    id: "v2", type: "Kalibrácia dôvery", dimension: "verifikacia", difficulty: 2,
    brief: "Píšeš úlohu z dejepisu. Pýtaš sa AI na dátum.",
    aiSays: "Štúrovci kodifikovali spisovnú slovenčinu v roku 1843.",
    aiCorrect: true,
    question: "Ako naložíš s touto odpoveďou?",
    options: [
      { text: "Použijem to bez váhania.", score: 1, reliance: true,
        feedback: "Tentokrát mala AI pravdu (1843). Ale stratégia 'vždy ver' zlyhá pri halucináciách — nedá sa na ňu spoľahnúť." },
      { text: "Znie to vierohodne, ale rýchlo overím v učebnici.", score: 2, correct: true,
        feedback: "Najlepší prístup — overovať systematicky, nielen keď tušíš chybu." },
      { text: "Odmietnem, AI nikdy neverím.", score: 0,
        feedback: "Prehnaná nedôvera je tiež chyba — vedie k zbytočnej práci a ignorovaniu správnych informácií." },
      { text: "Spýtam sa na zdroj a ten si overím.", score: 2, correct: true,
        feedback: "Dobré — kombinácia dopytu na zdroj a nezávislej kontroly." },
    ],
  },

  /* ---------- TYP 2: Hodnotenie zdroja (zdroje) ---------- */
  {
    id: "z1", type: "Hodnotenie zdroja", dimension: "zdroje", difficulty: 1,
    brief: "AI tvrdí, že 'pitie zelenej kávy zvýši tvoje IQ o 15 bodov za týždeň' a ponúka zdroje.",
    aiSays: "Tu sú zdroje, ktoré to potvrdzujú.",
    aiCorrect: false,
    question: "Ktorý zdroj je najdôveryhodnejší?",
    options: [
      { text: "Blog 'SuperZdravieMegaTip.sk' plný reklám na doplnky.", score: 0, reliance: false,
        feedback: "Konflikt záujmov (predáva doplnky) + žiadna recenzia. Nízka dôveryhodnosť." },
      { text: "Recenzovaná štúdia v odbornom časopise (N = 2000).", score: 2, correct: true,
        feedback: "Správne. Recenzovaný proces a veľká vzorka = najvyššia dôveryhodnosť z ponuky." },
      { text: "Video influencera s miliónom sledovateľov.", score: 0,
        feedback: "Popularita nie je dôkaz. Počet sledovateľov nevypovedá o pravdivosti." },
      { text: "Komentár pod článkom: 'mne to zabralo!'", score: 0,
        feedback: "Anekdota jedného človeka nie je dôkaz (vzorka = 1, žiadna kontrola)." },
    ],
  },
  {
    id: "z2", type: "Hodnotenie argumentu", dimension: "zdroje", difficulty: 3,
    brief: "AI ti pomáha s esejou a ponúka tento argument na použitie.",
    aiSays: "„Profesor X tvrdí, že táto diéta nefunguje. Ale veď on sám má nadváhu, takže jeho názoru sa neoplatí veriť.“",
    aiCorrect: false,
    question: "Použiješ tento argument?",
    options: [
      { text: "Áno, je presvedčivý.", score: 0, reliance: true,
        feedback: "Toto je klam ad hominem — útok na osobu namiesto na argument. Profesorova váha nesúvisí s pravdivosťou jeho tvrdenia." },
      { text: "Nie, je to klam ad hominem (útok na osobu).", score: 2, correct: true,
        feedback: "Správne! Rozpoznal si logický klam. Váha profesora nevyvracia jeho odborné tvrdenie." },
      { text: "Použijem, ale doplním ďalší dôkaz.", score: 1,
        feedback: "Lepšie by bolo klam úplne zahodiť — pridaním ďalšieho dôkazu sa klam nenapraví." },
      { text: "Nie som si istý, radšej ho preformulujem na vecný argument.", score: 2, correct: true,
        feedback: "Dobrá metakognícia — rozpoznanie, že s argumentom niečo nesedí a jeho oprava." },
    ],
  },

  /* ---------- TYP 3: Detekcia halucinácie (verifikacia) ---------- */
  {
    id: "h1", type: "Detekcia halucinácie", dimension: "verifikacia", difficulty: 2,
    brief: "AI napísala plynulý odsek o 2. svetovej vojne. Znie sebavedomo. Jedna veta je nepravdivá.",
    aiSays: "„Druhá svetová vojna sa začala v roku 1939. Slovensko bolo vtedy samostatný štát. Vojna v Európe sa skončila atómovým útokom na Berlín v máji 1945. USA vstúpili do vojny po útoku na Pearl Harbor.“",
    aiCorrect: false,
    question: "Ktorá veta je nesprávna?",
    options: [
      { text: "„...začala v roku 1939.“", score: 0, feedback: "Táto je správna (1. 9. 1939)." },
      { text: "„Slovensko bolo vtedy samostatný štát.“", score: 0, feedback: "Táto je správna (Slovenský štát 1939–1945)." },
      { text: "„...skončila atómovým útokom na Berlín v máji 1945.“", score: 2, correct: true,
        feedback: "Správne! Dvojitá chyba: atómové bomby padli na Hirošimu a Nagasaki (nie Berlín) a až v auguste. Vojna v Európe sa skončila kapituláciou Nemecka. Plynulý text ukrýva chybu." },
      { text: "„USA vstúpili po útoku na Pearl Harbor.“", score: 0, feedback: "Táto je správna (7. 12. 1941)." },
    ],
  },
  {
    id: "h2", type: "Detekcia halucinácie", dimension: "verifikacia", difficulty: 3,
    brief: "Pýtaš sa AI na vzorec. Odpoveď vyzerá odborne.",
    aiSays: "„Obsah kruhu vypočítaš ako S = 2·π·r. Je to základný vzorec z geometrie.“",
    aiCorrect: false,
    question: "Ako zareaguješ?",
    options: [
      { text: "Odpíšem vzorec, vyzerá odborne.", score: 0, reliance: true,
        feedback: "Pasca! 2·π·r je obvod kruhu, nie obsah. Obsah je π·r². Sebavedomý tón nezaručuje správnosť." },
      { text: "Zarazí ma to — obsah je predsa π·r², overím.", score: 2, correct: true,
        feedback: "Výborne. Zachytil si zámenu obvodu a obsahu. Toto je typická 'vierohodne znejúca' chyba AI." },
      { text: "Použijem, matematike AI určite rozumie.", score: 0, reliance: true,
        feedback: "AI bežne robí chyby aj v jednoduchej matematike. Dôvera v doménu nie je namieste." },
      { text: "Prepočítam si to na konkrétnom príklade (r = 1).", score: 2, correct: true,
        feedback: "Skvelá stratégia — overenie dosadením odhalí, že vzorec nesedí." },
    ],
  },

  /* ---------- TYP 4: Pravdepodobnostné uvažovanie ---------- */
  {
    id: "p1", type: "Pravdepodobnosť", dimension: "pravdepodobnost", difficulty: 3,
    brief: "Riešiš úlohu o testovaní. AI ti dá medzivýsledok.",
    aiSays: "Test na vzácnu chorobu je 99 % presný. Tvoj test je pozitívny. Chorobu má 1 z 10 000 ľudí.",
    aiCorrect: true,
    question: "Aká je približne pravdepodobnosť, že si naozaj chorý?",
    options: [
      { text: "Asi 99 %.", score: 0, reliance: true,
        feedback: "Klasická chyba — zanedbanie základnej miery (base rate). Choroba je veľmi vzácna, takže väčšina pozitívnych testov sú falošné poplachy." },
      { text: "Okolo 1 %.", score: 2, correct: true,
        feedback: "Správne! Pri prevalencii 1/10 000 a 1 % falošnej pozitivity je drvivá väčšina pozitívnych výsledkov falošná. Skutočná pravdepodobnosť je len ~1 %." },
      { text: "Presne 50 %.", score: 0, feedback: "Nie — to by platilo len pri úplne inom pomere prevalencie a chybovosti." },
      { text: "Neviem to z hlavy — dosadím do Bayesovho vzorca.", score: 1,
        feedback: "Poctivá metakognícia. Výpočet by ťa doviedol k ~1 %." },
    ],
  },
  {
    id: "p2", type: "Pravdepodobnosť", dimension: "pravdepodobnost", difficulty: 1,
    brief: "Rýchla otázka (typu CRT). AI mlčí — rozhodni sám.",
    aiSays: null,
    aiCorrect: null,
    question: "Pálka a loptička stoja spolu 1,10 €. Pálka stojí o 1,00 € viac ako loptička. Koľko stojí loptička?",
    options: [
      { text: "10 centov.", score: 0,
        feedback: "Intuitívna, ale nesprávna odpoveď. Keby loptička stála 10 c, pálka 1,10 € a spolu 1,20 €." },
      { text: "5 centov.", score: 2, correct: true,
        feedback: "Správne! Loptička 5 c + pálka 1,05 € = 1,10 €. Potlačil si rýchlu intuíciu — to je jadro reflektívneho myslenia." },
      { text: "1 euro.", score: 0, feedback: "Nie — to je rozdiel cien, nie cena loptičky." },
      { text: "55 centov.", score: 0, feedback: "Nie — skús rovnicu: loptička + (loptička + 1) = 1,10." },
    ],
  },

  /* ---------- TYP 5: Formulácia dopytu (prompting) ---------- */
  {
    id: "f1", type: "Formulácia promptu", dimension: "prompting", difficulty: 1,
    brief: "Máš napísať vlastnú esej o klimatickej zmene. Chceš od AI užitočný odrazový mostík.",
    aiSays: null, aiCorrect: null,
    question: "Ktorý prompt je najlepší?",
    options: [
      { text: "„Napíš mi celú esej o klimatickej zmene na 500 slov.“", score: 0, reliance: true,
        feedback: "Tým prenesieš celú úlohu na AI — nič sa nenaučíš a riskuješ plagiát." },
      { text: "„Daj mi 5 hlavných argumentov aj protiargumentov a ku každému zdroj, nech ich viem posúdiť.“", score: 2, correct: true,
        feedback: "Výborne — AI ako partner na myslenie. Dostaneš materiál, ktorý musíš spracovať a posúdiť sám." },
      { text: "„Aké je správne riešenie klimatickej zmeny?“", score: 0,
        feedback: "Príliš vágne a navádza na jednu 'správnu' odpoveď pri komplexnej téme." },
      { text: "„Sprav mi celý projekt aj s prezentáciou.“", score: 0, reliance: true,
        feedback: "Úplné offloadenie úlohy." },
    ],
  },
  {
    id: "f2", type: "Formulácia promptu", dimension: "prompting", difficulty: 2,
    brief: "Nerozumieš téme fotosyntéza a chceš sa ju naozaj naučiť.",
    aiSays: null, aiCorrect: null,
    question: "Ktorý prístup ťa naučí najviac?",
    options: [
      { text: "„Vysvetli mi fotosyntézu jednoducho a potom mi daj 3 kontrolné otázky, aby som si overil, či som pochopil.“", score: 2, correct: true,
        feedback: "Skvelé — pridávaš si spätnú väzbu a sebatestovanie. To podporuje skutočné učenie." },
      { text: "„Daj mi definíciu fotosyntézy, odpíšem ju.“", score: 0, reliance: true,
        feedback: "Odpísanie definície ≠ pochopenie. Žiadne overenie porozumenia." },
      { text: "„Je fotosyntéza dôležitá? Áno/nie.“", score: 0,
        feedback: "Nezmyselne úzka otázka, ktorá ťa nič nenaučí." },
      { text: "Požiadam o vysvetlenie a hneskôr si to skúsim vysvetliť vlastnými slovami niekomu inému.", score: 2, correct: true,
        feedback: "Feynmanova technika — vysvetliť niekomu inému je najlepší test porozumenia." },
    ],
  },

  /* ---------- TYP 6: Integrácia a etika ---------- */
  {
    id: "i1", type: "Integrácia a etika", dimension: "integracia", difficulty: 1,
    brief: "AI ti vygenerovala dobrý odsek do projektu, ktorý odovzdávaš pod svojím menom.",
    aiSays: "Tu je hotový odsek, ktorý môžeš použiť.",
    aiCorrect: true,
    question: "Čo s ním spravíš?",
    options: [
      { text: "Skopírujem ho 1:1 do projektu.", score: 0, reliance: true,
        feedback: "Bez overenia faktov a bez vlastného spracovania — etické riziko (plagiát) aj riziko prevzatia chyby." },
      { text: "Prečítam, overím fakty, prepíšem vlastnými slovami a uvediem použitie AI.", score: 2, correct: true,
        feedback: "Vzorové. Kritické spracovanie + transparentnosť = zodpovedné použitie AI." },
      { text: "Zmením pár slov, nech to softvér neodhalí.", score: 0,
        feedback: "Snaha skryť pôvod je nečestná a stále ide o prevzatie cudzej práce." },
      { text: "Použijem ho len ako inšpiráciu a napíšem vlastný, lepší odsek.", score: 2, correct: true,
        feedback: "Tiež správne — AI ako inšpirácia, nie ako náhrada vlastnej práce." },
    ],
  },
  {
    id: "i2", type: "Integrácia a etika", dimension: "integracia", difficulty: 2,
    brief: "Blíži sa termín. AI ti ponúkne hotové riešenie domácej úlohy z matematiky.",
    aiSays: "Tu je celé vypracované riešenie aj s postupom.",
    aiCorrect: true,
    question: "Ako sa zachováš, ak sa chceš na písomku naozaj pripraviť?",
    options: [
      { text: "Odpíšem riešenie a odovzdám.", score: 0, reliance: true,
        feedback: "Úlohu odovzdáš, ale na písomke (bez AI) zlyháš — naučil si sa nič. Klasický 'kognitívny dlh'." },
      { text: "Postup si naštudujem, potom vyriešim podobný príklad sám bez AI.", score: 2, correct: true,
        feedback: "Najlepšie — AI ti pomôže pochopiť, ale precvičíš sa samostatne. Tak budeš pripravený aj bez nej." },
      { text: "Pozriem len výsledok a skúsim k nemu dôjsť sám.", score: 2, correct: true,
        feedback: "Dobré — využiješ výsledok ako kontrolu, ale myslenie necháš na seba." },
      { text: "Odpíšem a 'naučím sa to potom'.", score: 0, reliance: true,
        feedback: "'Potom' zvyčajne nepríde. Odkladanie + offloadenie = nepripravenosť." },
    ],
  },

  /* ---------- TYP doplnkový: Testovanie hypotéz ---------- */
  {
    id: "ht1", type: "Testovanie hypotézy", dimension: "hypotezy", difficulty: 3,
    brief: "AI tvrdí: „Žiaci, ktorí používajú našu appku, majú lepšie známky — appka teda zlepšuje známky.“",
    aiSays: "Dáta to jasne potvrdzujú: používatelia appky majú v priemere lepšie známky.",
    aiCorrect: false,
    question: "Čo by NAJLEPŠIE overilo, či appka naozaj zlepšuje známky?",
    options: [
      { text: "Opýtať sa viacerých používateľov, či sú spokojní.", score: 0,
        feedback: "Spokojnosť nie je dôkaz účinku. Stále nevieš, či za známky môže appka." },
      { text: "Náhodne rozdeliť žiakov na tých s appkou a bez nej a porovnať známky.", score: 2, correct: true,
        feedback: "Správne — randomizovaný experiment. Možno appku používajú už aj tak lepší žiaci (korelácia ≠ kauzalita)." },
      { text: "Zistiť, koľko žiakov appku používa.", score: 0,
        feedback: "Počet používateľov nehovorí nič o účinku na známky." },
      { text: "Veriť dátam, čísla neklamú.", score: 0, reliance: true,
        feedback: "Čísla môžu klamať cez zlú interpretáciu. Toto je zámena korelácie a kauzality." },
    ],
  },
  {
    id: "ht2", type: "Testovanie hypotézy", dimension: "hypotezy", difficulty: 2,
    brief: "Kamarát tvrdí: „Vždy keď si dám šťastné ponožky, vyhráme zápas. Tie ponožky nás nesú.“",
    aiSays: null, aiCorrect: null,
    question: "Aký údaj by jeho tvrdenie najlepšie preveril?",
    options: [
      { text: "Koľkokrát vyhrali so šťastnými ponožkami.", score: 0,
        feedback: "Nestačí — musíš poznať aj prípady BEZ ponožiek, inak nevieš porovnať." },
      { text: "Koľkokrát vyhrali aj prehrali — so šťastnými ponožkami AJ bez nich.", score: 2, correct: true,
        feedback: "Správne — potrebuješ obe podmienky aj oba výsledky (úplná tabuľka), aby si vylúčil náhodu." },
      { text: "Akú farbu ponožky majú.", score: 0, feedback: "Irelevantné pre overenie účinku." },
      { text: "Ako sa kamarát po výhre cíti.", score: 0, feedback: "Pocit nie je dôkaz príčinnej súvislosti." },
    ],
  },
];

/* Sprístupnenie pre engine (plain script, bez modulov — funguje aj cez file://) */
window.DIMENZIE = DIMENZIE;
window.BANKA = BANKA;

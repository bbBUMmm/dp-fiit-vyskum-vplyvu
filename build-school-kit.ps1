# build-school-kit.ps1 -- assemble everything a Slovak school needs, in one folder.
#
# The thesis assignment requires the solution to be verified BY USING IT in a
# school. That is not a claim a repository can make about itself: a school
# receives a folder, not a git clone, and whatever is missing from that folder
# is missing on the day.
#
# So the kit is built, checked, and the check is what fails -- not the teacher.
#
#   .\build-school-kit.ps1                 build into .\school-kit
#   .\build-school-kit.ps1 -Verify         build and verify, no files copied if
#                                          anything required is absent
#
# What the school gets:
#   RUN.cmd                 one double-click to start a lesson
#   TEST.cmd                one double-click to administer a test
#   KODY.cmd                issue the pupil codes -- run by the SCHOOL, once
#   client\                 the exercise client, standard library only
#   test\                   the assessment module: banks, runner, scoring
#   tlac\                   everything that must be printed
#   kontrola\               the validator, to run the same afternoon
#   PRECITAJ-MA.txt         what to do, in order, in Slovak
#
# KODY.cmd is in the kit and not in the researcher's hands on purpose. The
# code-to-pupil mapping is the one thing that must never leave the school, so
# the school generates it. A kit that made the researcher issue the codes would
# put that mapping on the wrong laptop, and no amount of protocol prose would
# undo it.

param([switch]$Verify)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit  = Join-Path $root "school-kit"

# ---------------------------------------------------------------- required
# Every entry is checked before anything is copied. A kit that is 90 % built
# is worse than no kit: it looks ready.
$required = @(
    @{ From = "exercise-client\server.py";      To = "client\server.py" },
    @{ From = "exercise-client\pedagogy.py";    To = "client\pedagogy.py" },
    @{ From = "exercise-client\providers.py";   To = "client\providers.py" },
    @{ From = "exercise-client\events.py";      To = "client\events.py" },
    @{ From = "exercise-client\README.md";      To = "client\README.md" },
    @{ From = "mastersLaTeX\analysis\ingest.py"; To = "kontrola\ingest.py" },
    # --- the assessment module: without it the kit can teach but not measure
    @{ From = "assessment\bank.py";     To = "test\bank.py" },
    @{ From = "assessment\sessions.py"; To = "test\sessions.py" },
    @{ From = "assessment\linkage.py";  To = "test\linkage.py" },
    @{ From = "assessment\runner.py";   To = "test\runner.py" },
    @{ From = "assessment\scoring.py";  To = "test\scoring.py" },
    @{ From = "assessment\effort.py";   To = "test\effort.py" },
    @{ From = "assessment\integrity.py"; To = "test\integrity.py" },
    @{ From = "assessment\profiles.py"; To = "test\profiles.py" },
    @{ From = "assessment\report.py";   To = "test\report.py" }
)
$requiredDirs = @(
    @{ From = "exercise-client\static"; To = "client\static" },
    @{ From = "exercise-client\tasks";  To = "client\tasks" },
    @{ From = "assessment\banks";       To = "test\banks" },
    @{ From = "assessment\static";      To = "test\static" }
)

Write-Output "=== kontrola zdrojov ==="
$missing = @()
foreach ($f in $required) {
    $p = Join-Path $root $f.From
    if (-not (Test-Path $p)) { $missing += $f.From } else { Write-Output "  ok   $($f.From)" }
}
foreach ($d in $requiredDirs) {
    $p = Join-Path $root $d.From
    if (-not (Test-Path $p)) { $missing += $d.From } else { Write-Output "  ok   $($d.From)\" }
}
if ($missing.Count -gt 0) {
    Write-Output ""
    Write-Output "CHYBA: chybaju zdroje, kit sa nestavia:"
    $missing | ForEach-Object { Write-Output "  - $_" }
    exit 1
}
if ($Verify) { Write-Output "`nvsetky zdroje pritomne"; exit 0 }

# ---------------------------------------------------------------- assemble
if (Test-Path $kit) { Remove-Item $kit -Recurse -Force }
New-Item -ItemType Directory $kit | Out-Null
foreach ($sub in @("client", "test", "tlac", "kontrola", "data")) {
    New-Item -ItemType Directory (Join-Path $kit $sub) | Out-Null
}

foreach ($f in $required) {
    $dst = Join-Path $kit $f.To
    New-Item -ItemType Directory (Split-Path $dst -Parent) -Force | Out-Null
    Copy-Item (Join-Path $root $f.From) $dst
}
foreach ($d in $requiredDirs) {
    Copy-Item (Join-Path $root $d.From) (Join-Path $kit $d.To) -Recurse
}

# ---------------------------------------------------------------- launcher
# A .cmd rather than a .ps1: double-clicking a .ps1 opens Notepad on a default
# Windows install, which is exactly the kind of detail that stops a session.
$runCmd = @'
@echo off
chcp 65001 >nul
rem UTF-8 for Python too: the lesson topics are Slovak and a narrow
rem stdout kills the server before it serves anything.
set PYTHONIOENCODING=utf-8
title Vyskum AI vo vyucbe -- spustenie hodiny
cd /d "%~dp0client"

echo ============================================================
echo   Vyskum vplyvu nastrojov umelej inteligencie
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo CHYBA: Python nie je nainstalovany alebo nie je v PATH.
  echo Nainstalujte Python 3.11+ z python.org a zaskrtnite
  echo "Add Python to PATH". Potom spustite tento subor znova.
  echo.
  pause
  exit /b 1
)

set /p COND="Podmienka (K = bez asistenta, G = genericky, A = adaptivny): "
set /p SESSION="Oznacenie hodiny (napr. 2026-10-07-2A-P1): "
set /p SALT="Sol pre pseudonymizaciu (drzi ju skola): "

if "%SALT%"=="" (
  echo.
  echo CHYBA: bez soli sa zber nespusti. Sol drzi skola, nie vyskumnik.
  pause
  exit /b 1
)

echo.
echo Spustam... Otvorte v prehliadaci:  http://127.0.0.1:5173/
echo Ukoncenie: zatvorte toto okno.
echo.
python server.py --condition %COND% --session "%SESSION%" --salt "%SALT%" --log "..\data\events_%SESSION%.jsonl"
pause
'@
Set-Content -Path (Join-Path $kit "RUN.cmd") -Value $runCmd -Encoding UTF8

# ------------------------------------------------------------------ test runner
# A separate launcher from RUN.cmd on purpose. The lesson and the test are
# different events with different rules: during the test the assistant must not
# be reachable, and a single entry point that could start either is one wrong
# keystroke away from invalidating the measurement.
$testCmd = @'
@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Vyskum AI vo vyucbe -- test
cd /d "%~dp0test"

echo ============================================================
echo   Test -- POZOR: asistent musi byt v tomto case nedostupny
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo CHYBA: Python nie je nainstalovany alebo nie je v PATH.
  echo Nainstalujte Python 3.11+ z python.org a zaskrtnite
  echo "Add Python to PATH". Potom spustite tento subor znova.
  echo.
  pause
  exit /b 1
)

echo Ktory test chcete spustit?
echo    1  predtest k teme        (5 poloziek,  pred hodinou)
echo    2  okamzity test          (12 poloziek, hned po hodine)
echo    3  odlozeny test          (12 poloziek, po troch tyzdnoch)
echo    4  transferovy test       (6 poloziek,  25 minut)
echo    5  test kritickeho myslenia (12 poloziek)
echo.
set /p WHICH="Cislo: "

if "%WHICH%"=="1" set BANK=T1_PRECHECK
if "%WHICH%"=="2" set BANK=T1_IPT
if "%WHICH%"=="3" set BANK=T1_DRT
if "%WHICH%"=="4" set BANK=TT
if "%WHICH%"=="5" set BANK=CT
if "%BANK%"=="" (
  echo.
  echo CHYBA: neplatna volba.
  pause
  exit /b 1
)

set /p SESSION="Oznacenie stretnutia (napr. P1, T4a): "
set /p SKOLA="Dvojznakovy kod skoly (z obalky, napr. GY): "

if not exist "..\data\kody-%SKOLA%.txt" (
  echo.
  echo CHYBA: nenasiel som zoznam kodov ..\data\kody-%SKOLA%.txt
  echo Spustite najprv KODY.cmd. Zoznam kodov vytvara SKOLA, nie vyskumnik.
  echo.
  pause
  exit /b 1
)

echo.
echo Spustam... Ziaci otvoria v prehliadaci:  http://127.0.0.1:5174/
echo Ukoncenie: zatvorte toto okno az po poslednom ziakovi.
echo.
python runner.py --bank %BANK% --session "%SESSION%" --school "%SKOLA%" ^
       --codes "..\data\kody-%SKOLA%.txt" ^
       --log "..\data\odpovede_%SESSION%_%BANK%.jsonl"
pause
'@
Set-Content -Path (Join-Path $kit "TEST.cmd") -Value $testCmd -Encoding UTF8

# ------------------------------------------------------------------ codes
# Run by the school, once, before anything else. The output file pairs a code
# with a pupil; it stays in the school and the researcher never receives it.
$kodyCmd = @'
@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Vydanie kodov ziakom -- robi SKOLA
cd /d "%~dp0test"

echo ============================================================
echo   Vydanie kodov ziakom
echo ------------------------------------------------------------
echo   Tento subor spusta KONTAKTNA OSOBA SKOLY, nie vyskumnik.
echo   Vznikne dvojica suborov:
echo
echo     ..\data\kody-XX.txt        len kody  -- ide vyskumnikovi
echo     ..\data\ZOZNAM-kody-XX.csv kod + miesto pre meno
echo                                -- ZOSTAVA V SKOLE
echo
echo   Druhy subor nikdy neposielajte vyskumnikovi. Je to jediny
echo   most medzi kodom a ziakom a ma zostat v skole.
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo CHYBA: Python nie je nainstalovany alebo nie je v PATH.
  pause
  exit /b 1
)

set /p SKOLA="Dvojznakovy kod skoly (vymyslite, napr. GY): "
set /p POCET="Pocet ziakov (s rezervou, napr. 30): "

python -c "import sys, linkage; s=sys.argv[1].upper(); n=int(sys.argv[2]); c=linkage.issue(s,n); open(r'..\data\kody-%%s.txt'%%s,'w',encoding='utf-8').write('\n'.join(c)+'\n'); f=open(r'..\data\ZOZNAM-kody-%%s.csv'%%s,'w',encoding='utf-8-sig'); f.write('kod;meno ziaka (vyplni skola)\n'); [f.write(x+';\n') for x in c]; f.close(); print('Vydanych kodov:', len(c))" "%SKOLA%" "%POCET%"

if errorlevel 1 (
  echo.
  echo CHYBA pri vydavani kodov.
  pause
  exit /b 1
)

echo.
echo Hotovo. Vytlacte ZOZNAM-kody-%SKOLA%.csv, rozstrihajte na obalky,
echo a kopiu s menami si ponechajte v skole.
echo.
pause
'@
Set-Content -Path (Join-Path $kit "KODY.cmd") -Value $kodyCmd -Encoding UTF8

# ---------------------------------------------------------------- checker
$checkCmd = @'
@echo off
chcp 65001 >nul
title Kontrola zozbieranych udajov
cd /d "%~dp0"
echo Kontrolujem priecinok ..\data ...
echo.
python ingest.py --check "..\data"
echo.
echo Kontrolu spustite v DEN ZBERU. Chyba najdena dnes sa da opravit
echo telefonatom; chyba najdena v marci sa opravit neda.
pause
'@
Set-Content -Path (Join-Path $kit "kontrola\SKONTROLUJ.cmd") -Value $checkCmd -Encoding UTF8

# ---------------------------------------------------------------- readme
$readme = @'
VYSKUM VPLYVU NASTROJOV UMELEJ INTELIGENCIE VO VYUCBE
=====================================================

Co je v tomto priecinku a v akom poradi to pouzit.


PRED ZBEROM
-----------
1. Vytlacte vsetko z priecinka  tlac\
   - suhlas pre zakonneho zastupcu (jeden na ziaka)
   - suhlas ziaka
   - pokyny pre ucitela
   - kontrolny list vernosti (jeden na kazdy vyucovaci blok)

2. Rozdajte suhlasy. Trieda sa zaraduje len ak sa vrati aspon 85 % suhlasov.

3. Vygenerujte sol pre pseudonymizaciu a ULOZTE JU V SKOLE.
   Sol drzi skola. Vyskumnik ju nema a nesmie mat -- bez nej sa kody
   ziakov neda spatne priradit k menam, a to je zamer.

4. Spustite  KODY.cmd  (dvojklik). Toto robi SKOLA, nie vyskumnik.

   Zadajte dvojznakovy kod skoly (vymyslite si, napr. GY) a pocet
   ziakov s rezervou. Vzniknu dva subory v priecinku  data\ :

     kody-XX.txt          len kody            -> ide vyskumnikovi
     ZOZNAM-kody-XX.csv   kod + miesto na meno -> ZOSTAVA V SKOLE

   Druhy subor je jediny most medzi kodom a ziakom. Nikdy ho
   neposielajte vyskumnikovi. Vytlacte ho, rozstrihajte na obalky,
   a kopiu s menami si ulozte.

   Kody su navrhnute tak, aby sa preklep odmietol hned pri zadavani:
   nie su v nich znaky, ktore sa zamieňaju (O/0, I/1/L, S/5, Z/2, B/8),
   a posledny znak je kontrolny. Ziak teda nemoze omylom zadat kod
   niekoho ineho -- prepise si svoj.


POCAS ZBERU
-----------
HODINA a TEST su dva rozne spustace. Nie je to zbytocne: pocas testu
musi byt asistent nedostupny, a jeden spustac pre oboje by znamenal, ze
jeden zly stisk klavesy znehodnoti meranie.

5. HODINA -- na kazdom notebooku spustite  RUN.cmd  (dvojklik).
   Zadajte podmienku, oznacenie hodiny a sol.
   Ziaci otvoria v prehliadaci:  http://127.0.0.1:5173/
   Ucitel vedie hodinu podla pokynov a priebezne vyplna kontrolny list.

6. TEST -- spustite  TEST.cmd  (dvojklik).
   Vyberte, ktory test sa pise, zadajte oznacenie stretnutia a kod skoly.
   Ziaci otvoria v prehliadaci:  http://127.0.0.1:5174/
   Ziak zada svoj kod z obalky. Ak sa preklepne, nastroj to povie a
   necha ho prepisat -- preto sa kod nezadava za ucitela.

   POCAS TESTU:
     - asistent musi byt nedostupny (v podmienke K je skryty vzdy)
     - ziaci nemaju mat pri sebe telefon ani poznamky
     - vysledok sa ziakovi nezobrazi; je to zamer, nie chyba.
       Test, ktory dava spatnu vazbu, je ucebna udalost, a tento
       sedi medzi dvoma meraniami ucenia.

   Predtest k teme sa pise na konci PREDCHADZAJUCEJ hodiny
   informatiky, nie v tomto bloku -- v bloku na neho nie je miesto.


PO ZBERE -- EST TEN ISTY DEN
----------------------------
9. Spustite  kontrola\SKONTROLUJ.cmd

   Toto je najdolezitejsi krok celeho postupu. Kontrola najde chybajuci
   stlpec, preklep v kode alebo chybajuci suhlas, kym je trieda este
   dostupna. Ta ista chyba najdena pri analyze o niekolko mesiacov uz
   opravit neda -- z opravitelnej administrativnej chyby sa stane
   trvalo chybajuci udaj.

   Kontrola rozlisuje:
     CHYBA       treba zasiahnut (napr. odpoved bez suhlasu -> riadok sa maze)
     UPOZORNENIE zber je v poriadku, ale blok sa spracuje inak

10. Z priecinka  data\  odovzdajte vsetko OKREM suboru
    ZOZNAM-kody-XX.csv. Ten zostava v skole.
    Odovzdavane subory neobsahuju mena ani triedy po mene.


CO SA ZAZNAMENAVA A CO NIE
--------------------------
Zaznamenava sa:  pseudonym (kod hasovany solou), odpovede, casy,
                 prompty odoslane nastroju, vlastne vysvetlenia ziaka.

Nezaznamenava sa: meno, rodne cislo, trieda po mene, nic z toho, co
                 ziak robi mimo cviceneho rozhrania.

Ziak moze kedykolvek prestat bez akehokolvek nasledku pre znamku.
Suhlas je odvolatelny; po odvolani sa zaznamy daneho pseudonymu
vymazu do 30 dni.


KED NIECO NEFUNGUJE
-------------------
Vypadne internet
  Podmienka K pokracuje bez zmeny.
  Podmienky G a A sa prerusia, hodina sa dovedie do konca bez asistenta
  a cely blok triedy sa vyradi z analyzy podla protokolu. Nenahradza sa
  inym terminom -- perioda je sucastou dizajnu.

Ziak chyba na jednej perióde
  Zostava v studii. Chybajuca perioda sa osetri v analyze.

Ziak chyba na odlozenom teste
  Ponuknite nahradny termin do jedneho tyzdna a zapiste odstup.

Chyba suhlas
  Ziak absolvuje hodinu ako ktorykolvek iny; nezaznamenava sa onho nic.

Python nie je nainstalovany
  RUN.cmd aj TEST.cmd to povedia a skoncia. Nainstalujte Python 3.11+
  z python.org a zaskrtnite "Add Python to PATH".

Ziak stratil obalku s kodom
  Kontaktna osoba skoly najde jeho kod v  ZOZNAM-kody-XX.csv  a vypise
  mu ho znova. Vyskumnik to urobit nemoze a nema mat ako.

Ziak zada kod a nastroj ho odmietne
  Nechajte ho prepisat kod znak po znaku. Nastroj povie, co je zle --
  napriklad ze v kodoch nie je pismeno O, takze to ma byt nula.
  Nezadavajte kod za ziaka a nehadajte: zle zadany kod znamena, ze sa
  jeho vysledok neda spojit s jeho ostatnymi hodinami.
'@
Set-Content -Path (Join-Path $kit "PRECITAJ-MA.txt") -Value $readme -Encoding UTF8

# ---------------------------------------------------------------- print set
# Placeholders that name their source, so a missing PDF is obvious rather than
# silently absent on the day.
$tlacList = @(
    "suhlas-zakonny-zastupca.pdf   <- priloha E tezy, cast 'Informovany suhlas zakonneho zastupcu'",
    "suhlas-ziak.pdf               <- priloha E tezy, cast 'Suhlas ziaka'",
    "pokyny-ucitel.pdf             <- priloha D tezy (scenare hodin) + priloha F (protokol)",
    "kontrolny-list-vernosti.pdf   <- priloha F tezy",
    "karty-s-kodmi.pdf             <- vytlacte ZOZNAM-kody-XX.csv, ktory
                                 vytvori KODY.cmd, a rozstrihajte na obalky.
                                 Kopiu s menami si ponechajte v skole."
)
Set-Content -Path (Join-Path $kit "tlac\CO-VYTLACIT.txt") `
    -Value ("Do tohto priecinka patria nasledujuce vytlacene materialy:`r`n`r`n" +
            ($tlacList -join "`r`n") +
            "`r`n`r`nAk tu nieco chyba, zber sa nezacina.") -Encoding UTF8

# ---------------------------------------------------------------- verify
Write-Output ""
Write-Output "=== kontrola zostaveneho kitu ==="
$expect = @("RUN.cmd", "TEST.cmd", "KODY.cmd", "PRECITAJ-MA.txt",
            "client\server.py", "client\static", "client\tasks",
            "test\runner.py", "test\bank.py", "test\linkage.py",
            "test\banks", "test\static\test.html",
            "kontrola\ingest.py", "kontrola\SKONTROLUJ.cmd",
            "tlac\CO-VYTLACIT.txt", "data")
$bad = @()
foreach ($e in $expect) {
    if (Test-Path (Join-Path $kit $e)) { Write-Output "  ok   $e" } else { $bad += $e }
}
if ($bad.Count -gt 0) {
    Write-Output ""
    $bad | ForEach-Object { Write-Output "  CHYBA $_" }
    exit 1
}

# The kit must also WORK, not merely contain the files. A folder whose Python
# cannot import is a folder that fails in the classroom, and the import graph is
# the part that breaks when a file is copied to a flatter directory than the one
# it was written in. So the modules are imported, the banks are loaded, and a
# code is issued and verified -- from inside the kit, with nothing else on the
# path.
Write-Output ""
Write-Output "=== kontrola funkcnosti kitu ==="
$probe = @'
import json, sys
sys.path.insert(0, ".")
import bank, linkage, sessions, scoring, profiles, report, effort, integrity
banks = bank.load_all()
b = sessions.budget()
code = linkage.issue("GY", 1, seed=1)[0]
assert linkage.verify(code, "GY")
try:
    linkage.verify(code[:-1] + ("4" if code[-1] != "4" else "7"), "GY")
    raise SystemExit("a mistyped code was accepted")
except linkage.CodeError:
    pass
print(json.dumps({"banks": len(banks),
                  "items": sum(x.n_items for x in banks.values()),
                  "sessions_fit": b["all_fit"],
                  "code": code}, ensure_ascii=False))
'@
$probePath = Join-Path $kit "test\_probe.py"
Set-Content -Path $probePath -Value $probe -Encoding UTF8
Push-Location (Join-Path $kit "test")
$env:PYTHONIOENCODING = "utf-8"
$probeOut = & python _probe.py 2>&1 | Out-String
$probeCode = $LASTEXITCODE
Pop-Location
Remove-Item $probePath -Force
if ($probeCode -ne 0) {
    Write-Output "  CHYBA: kit sa nedaruje spustit z vlastneho priecinka"
    ($probeOut -split "`n" | Select-Object -Last 12) | ForEach-Object { Write-Output "  ! $_" }
    exit 1
}
Write-Output ("  ok   moduly sa importuju, zasobniky sa citaju, kod sa overuje")
Write-Output ("       " + $probeOut.Trim())

$n = (Get-ChildItem $kit -Recurse -File | Measure-Object).Count
$mb = [math]::Round((Get-ChildItem $kit -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 2)
Write-Output ""
Write-Output "kit zostaveny: $kit"
Write-Output "$n suborov, $mb MB"
Write-Output ""
Write-Output "ZOSTAVA DOPLNIT RUCNE: vytlacene materialy do  school-kit\tlac\"
Write-Output "  (zoznam je v  school-kit\tlac\CO-VYTLACIT.txt)"

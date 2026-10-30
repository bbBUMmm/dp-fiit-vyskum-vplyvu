@echo off
set PYTHONIOENCODING=utf-8
title Vydanie kodov ziakom -- robi SKOLA
cd /d "%~dp0test"

echo ============================================================
echo   Vydanie kodov ziakom
echo ------------------------------------------------------------
echo   Tento subor spusta KONTAKTNA OSOBA SKOLY, nie vyskumnik.
echo   Vznikne dvojica suborov:
echo.
echo     ..\data\kody-XX.txt        len kody  -- ide vyskumnikovi
echo     ..\data\ZOZNAM-kody-XX.csv kod + miesto pre meno
echo                                -- ZOSTAVA V SKOLE
echo.
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

set SKOLA=
set POCET=
set /p SKOLA="Dvojznakovy kod skoly (vymyslite, napr. GY): "
set /p POCET="Pocet ziakov (s rezervou, napr. 30): "
if "%POCET%"=="" (
  echo CHYBA: zadajte pocet ziakov.
  pause
  exit /b 1
)

if exist "..\data\kody-%SKOLA%.txt" (
  echo.
  echo POZOR: kody pre skolu %SKOLA% uz existuju. Nove kody by sa nezhodovali
  echo s obalkami, ktore ziaci uz maju. Ak naozaj chcete nove, najprv
  echo presunte stary subor ..\data\kody-%SKOLA%.txt inam.
  pause
  exit /b 1
)

rem UTF-8 console only now: set /p misreads input under code page 65001
chcp 65001 >nul
python -c "import sys, linkage; s=sys.argv[1].upper(); n=int(sys.argv[2]); c=linkage.issue(s,n); open(r'..\data\kody-%%s.txt'%%s,'w',encoding='utf-8').write('\n'.join(c)+'\n'); f=open(r'..\data\ZOZNAM-kody-%%s.csv'%%s,'w',encoding='utf-8-sig'); f.write('kod;meno ziaka (vyplni skola)\n'); [f.write(x+';\n') for x in c]; f.close(); print('Vydanych kodov:', len(c))" "%SKOLA%" "%POCET%"

if errorlevel 1 (
  echo.
  echo CHYBA pri vydavani kodov. Kod skoly su dve pismena alebo cislice
  echo bez zamenitelnych znakov O 0 I 1 L S 5 Z 2 B 8, pocet je cele cislo.
  pause
  exit /b 1
)

echo.
echo Hotovo. Vytlacte ZOZNAM-kody-%SKOLA%.csv, rozstrihajte na obalky,
echo a kopiu s menami si ponechajte v skole.
echo.
pause

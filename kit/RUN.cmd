@echo off
rem UTF-8 for Python too: the lesson topics are Slovak and a narrow
rem stdout kills the server before it serves anything.
set PYTHONIOENCODING=utf-8
title Vyskum AI vo vyucbe -- hodina
cd /d "%~dp0client"

echo ============================================================
echo   Vyskum vplyvu nastrojov umelej inteligencie -- HODINA
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

echo Predmet a hodina:
echo    1  Informatika - vyhladavanie v poli (T1)
echo    2  Matematika  - zlozene urokovanie (navrh)
echo    3  Fyzika      - seriove a paralelne zapojenie (navrh)
set TASKS=
set /p PRED="Cislo: "
if "%PRED%"=="1" set TASKS=tasks\t1_search.json
if "%PRED%"=="2" set TASKS=tasks\m1_interest.json
if "%PRED%"=="3" set TASKS=tasks\f1_circuits.json
if "%TASKS%"=="" (
  echo CHYBA: neplatna volba.
  pause
  exit /b 1
)

set COND=
set /p COND="Podmienka (K = bez asistenta, G = genericky, A = adaptivny): "
if /i "%COND%"=="k" set COND=K
if /i "%COND%"=="g" set COND=G
if /i "%COND%"=="a" set COND=A
if not "%COND%"=="K" if not "%COND%"=="G" if not "%COND%"=="A" (
  echo CHYBA: podmienka musi byt K, G alebo A.
  pause
  exit /b 1
)

set SESSION=
set /p SESSION="Oznacenie hodiny (napr. 2026-10-07-2A-P1): "
if "%SESSION%"=="" (
  echo CHYBA: oznacenie hodiny je povinne.
  pause
  exit /b 1
)

set SKOLA=
set /p SKOLA="Dvojznakovy kod skoly (napr. GY; Enter = bez kontroly kodov): "
set SALT=
set /p SALT="Sol pre pseudonymizaciu (drzi ju skola): "
if "%SALT%"=="" (
  echo.
  echo CHYBA: bez soli sa zber nespusti. Sol drzi skola, nie vyskumnik.
  pause
  exit /b 1
)

echo.
echo Rezim:
echo    1  cela trieda - ziaci sa pripoja cez skolsku siet (pocitace aj mobily)
echo    2  len tento pocitac
set MODE=1
set /p MODE="Cislo [1]: "
set HOST=0.0.0.0
if "%MODE%"=="2" set HOST=127.0.0.1

set SCHOOLARG=
if not "%SKOLA%"=="" set SCHOOLARG=--school %SKOLA%
set CODESARG=
if not "%SKOLA%"=="" if exist "..\data\kody-%SKOLA%.txt" set CODESARG=--codes "..\data\kody-%SKOLA%.txt"
rem codes with BOTH signed consents; a code that is not listed is never recorded
set CONSENTARG=
if not "%SKOLA%"=="" if exist "..\data\suhlasy-%SKOLA%.txt" set CONSENTARG=--consent-list "..\data\suhlasy-%SKOLA%.txt"

echo.
echo Spustam... Adresu pre ziakov aj PIN pre panel ucitela uvidite nizsie.
echo Ukoncenie: zatvorte toto okno az po skonceni hodiny.
echo.
rem UTF-8 console only now: set /p misreads input under code page 65001
chcp 65001 >nul
python server.py --condition %COND% --tasks "%TASKS%" --session "%SESSION%" %SCHOOLARG% %CODESARG% %CONSENTARG% --salt "%SALT%" --host %HOST% --log "..\data\events_%SESSION%.jsonl"
pause

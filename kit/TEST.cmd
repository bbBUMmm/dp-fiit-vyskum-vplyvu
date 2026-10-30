@echo off
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

echo Ktory test alebo dotaznik chcete spustit?
echo    0  SEKCIA TESTY: testy k temam (T1 pred hodinou, T3 po hodine,
echo       T4 po troch tyzdnoch) a dotazniky -- vyber v dalsom kroku
echo    1  predtest k teme            (5 poloziek,  pred hodinou)
echo    2  okamzity test              (12 poloziek, hned po hodine)
echo    3  odlozeny test              (12 poloziek, po troch tyzdnoch)
echo    4  transferovy test           (6 poloziek,  25 minut)
echo    5  test kritickeho myslenia   (12 poloziek)
echo    6  dotaznik po hodine         (zataz, pocit naucenia; 7 minut)
echo    7  dotaznik metakognicie      (Jr. MAI)
echo    8  vstupny dotaznik           (doterajsie pouzivanie AI)
echo.
set BANK=
set TESTARG=
set /p WHICH="Cislo: "

if "%WHICH%"=="0" set TESTARG=--test vyber
if "%WHICH%"=="1" set BANK=T1_PRECHECK
if "%WHICH%"=="2" set BANK=T1_IPT
if "%WHICH%"=="3" set BANK=T1_DRT
if "%WHICH%"=="4" set BANK=TT
if "%WHICH%"=="5" set BANK=CT
if "%WHICH%"=="6" set BANK=POST_LESSON
if "%WHICH%"=="7" set BANK=JRMAI
if "%WHICH%"=="8" set BANK=BACKGROUND
if "%BANK%"=="" if "%TESTARG%"=="" (
  echo.
  echo CHYBA: neplatna volba.
  pause
  exit /b 1
)

set CONDARG=
if not "%BANK%"=="POST_LESSON" goto nocond
set COND=
set /p COND="Podmienka hodiny, po ktorej sa dotaznik vyplna (K, G alebo A): "
if /i "%COND%"=="k" set COND=K
if /i "%COND%"=="g" set COND=G
if /i "%COND%"=="a" set COND=A
if not "%COND%"=="K" if not "%COND%"=="G" if not "%COND%"=="A" (
  echo CHYBA: podmienka musi byt K, G alebo A. V podmienke K sa otazky o asistentovi vynechaju.
  pause
  exit /b 1
)
set CONDARG=--condition %COND%
:nocond

set SESSION=
set /p SESSION="Oznacenie stretnutia (napr. P1, T4a): "
if "%SESSION%"=="" (
  echo CHYBA: oznacenie stretnutia je povinne.
  pause
  exit /b 1
)
set SKOLA=
set /p SKOLA="Dvojznakovy kod skoly (z obalky, napr. GY): "
set SALT=
set /p SALT="Sol pre pseudonymizaciu (ta ista ako pri hodine): "
if "%SALT%"=="" (
  echo CHYBA: bez soli sa test nespusti. Sol drzi skola.
  pause
  exit /b 1
)

if not exist "..\data\kody-%SKOLA%.txt" (
  echo.
  echo CHYBA: nenasiel som zoznam kodov ..\data\kody-%SKOLA%.txt
  echo Spustite najprv KODY.cmd. Zoznam kodov vytvara SKOLA, nie vyskumnik.
  echo.
  pause
  exit /b 1
)

echo.
echo Rezim:
echo    1  cela trieda - ziaci sa pripoja cez skolsku siet
echo    2  len tento pocitac
set MODE=1
set /p MODE="Cislo [1]: "
set HOST=0.0.0.0
if "%MODE%"=="2" set HOST=127.0.0.1

echo.
rem codes with BOTH signed consents; a code that is not listed is never recorded
set CONSENTARG=
if exist "..\data\suhlasy-%SKOLA%.txt" set CONSENTARG=--consent-list "..\data\suhlasy-%SKOLA%.txt"

echo Spustam... Ziaci otvoria adresu tohto pocitaca, port 5174
echo (v rezime 2: http://127.0.0.1:5174/).
echo Ukoncenie: zatvorte toto okno az po poslednom ziakovi.
echo.
rem the test section picks the test (and, for T3, the condition) in the console
set BANKARG=
set LOGARG=--log-dir "..\data"
if not "%BANK%"=="" set BANKARG=--bank %BANK%
if not "%BANK%"=="" set LOGARG=--log "..\data\odpovede_%SESSION%_%BANK%.jsonl"
rem UTF-8 console only now: set /p misreads input under code page 65001
chcp 65001 >nul
python runner.py %BANKARG% %TESTARG% --session "%SESSION%" --school "%SKOLA%" %CONDARG% --salt "%SALT%" --host %HOST% --codes "..\data\kody-%SKOLA%.txt" %CONSENTARG% %LOGARG%
pause

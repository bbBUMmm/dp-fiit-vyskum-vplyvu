@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Kontrola zozbieranych udajov
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo CHYBA: Python nie je nainstalovany alebo nie je v PATH.
  pause
  exit /b 1
)

echo Kontrolujem priecinok ..\data ...
echo.
python datacheck.py "..\data"
echo.
echo Kontrolu spustite v DEN ZBERU. Chyba najdena dnes sa da opravit
echo telefonatom; chyba najdena v marci sa opravit neda.
pause

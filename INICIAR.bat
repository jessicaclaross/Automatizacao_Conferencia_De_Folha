@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

set "PYTHON_CMD="

where py >nul 2>&1
if %errorlevel%==0 set "PYTHON_CMD=py -3"

if not defined PYTHON_CMD (
    where python >nul 2>&1
    if %errorlevel%==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo.
    echo [ERRO] Python nao encontrado.
    pause
    exit /b 1
)

echo Instalando dependencias...
%PYTHON_CMD% -m pip install -r requirements.txt

echo.
echo PYTHON UTILIZADO:
%PYTHON_CMD% -c "import sys; print(sys.executable)"

echo.
echo Abrindo o sistema...
%PYTHON_CMD% app.py

if errorlevel 1 pause
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
    echo Instale em https://www.python.org/downloads/
    echo Na instalacao, marque "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Instalando dependencias (se necessario)...
%PYTHON_CMD% -m pip install -r requirements.txt -q

echo Abrindo o sistema...
%PYTHON_CMD% app.py
if errorlevel 1 pause

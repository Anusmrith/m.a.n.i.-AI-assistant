@echo off
title M.A.N.I. Personal AI Assistant (Windows)
cd /d "%~dp0"

echo ===================================================
echo       Launching M.A.N.I. Personal AI Assistant
echo ===================================================

:: Ensure .env exists from template if first time
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Setting up initial .env configuration...
        copy ".env.example" ".env" >nul
    )
)

:: Check if virtual environment already exists
if exist ".venv\Scripts\python.exe" goto :RUN_APP

:: Virtual environment not found; discover a working Python installation
echo [*] First-time setup detected. Configuring Python environment...

set "PYTHON_EXE="

:: 1. Try py launcher
py -3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py -3"
    goto :CREATE_VENV
)

:: 2. Try python command
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :CREATE_VENV
)

:: 3. Scan common Windows Python installation directories
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" --version >nul 2>&1
        if %errorlevel% equ 0 (
            set "PYTHON_EXE="%%D\python.exe""
            goto :CREATE_VENV
        )
    )
)

for /d %%D in ("C:\Program Files\Python*") do (
    if exist "%%D\python.exe" (
        "%%D\python.exe" --version >nul 2>&1
        if %errorlevel% equ 0 (
            set "PYTHON_EXE="%%D\python.exe""
            goto :CREATE_VENV
        )
    )
)

echo [ERROR] No working Python 3.10+ installation found.
echo Please install Python from https://www.python.org/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:CREATE_VENV
echo [*] Creating virtual environment (.venv) using %PYTHON_EXE%...
%PYTHON_EXE% -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [*] Installing required packages from requirements.txt...
.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
.venv\Scripts\pip.exe install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Some dependencies had warnings during installation.
)
echo [*] Setup complete!
echo.

:RUN_APP
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

echo [*] Starting M.A.N.I. Windows Desktop Assistant...
.venv\Scripts\python.exe run_jarvis.py

if %errorlevel% neq 0 (
    echo.
    echo [!] M.A.N.I. stopped with exit code %errorlevel%.
    pause
)

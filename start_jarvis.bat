@echo off
title M.A.N.I. Personal AI Assistant (Windows)
cd /d "%~dp0"

echo ===================================================
echo       Launching M.A.N.I. Personal AI Assistant
echo ===================================================

:: Check for Python installation
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.10+ from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Ensure .env exists from template if first time
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Setting up initial .env configuration...
        copy ".env.example" ".env" >nul
    )
)

:: Check if virtual environment exists; if not, create it and install requirements
if not exist ".venv\Scripts\python.exe" (
    echo [*] First-time setup detected. Configuring Python environment...
    echo [*] Creating virtual environment (.venv)...
    python -m venv .venv
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
)

chcp 65001 >nul
set PYTHONIOENCODING=utf-8

echo [*] Starting M.A.N.I. Windows Desktop Assistant...
.venv\Scripts\python.exe run_jarvis.py

if %errorlevel% neq 0 (
    echo.
    echo [!] M.A.N.I. stopped with exit code %errorlevel%.
    pause
)

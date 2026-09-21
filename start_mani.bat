@echo off
title M.A.N.I. Personal AI Assistant
cd /d "%~dp0"

echo ===================================================
echo       Launching M.A.N.I. Personal Assistant
echo ===================================================

if not exist ".venv\Scripts\python.exe" (
    echo Error: Python virtual environment not found in .venv.
    echo Please run setup first.
    pause
    exit /b 1
)

chcp 65001 >nul
set PYTHONIOENCODING=utf-8

.venv\Scripts\python.exe run_jarvis.py
pause

# PowerShell launcher for M.A.N.I.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "      Launching M.A.N.I. Personal Assistant        " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Error: Python virtual environment not found in .venv." -ForegroundColor Red
    pause
    exit 1
}

& ".venv\Scripts\python.exe" run_jarvis.py

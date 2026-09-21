# PowerShell launcher for M.A.N.I. Personal AI Assistant
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "      Launching M.A.N.I. Personal AI Assistant    " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# Check for virtual environment or global Python
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        Write-Host "[ERROR] Python was not found in your PATH." -ForegroundColor Red
        Write-Host "Please install Python 3.10+ from https://www.python.org/" -ForegroundColor Yellow
        pause
        exit 1
    }
}

# Ensure .env exists
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Write-Host "[*] Copying initial .env configuration..." -ForegroundColor Gray
    Copy-Item ".env.example" ".env"
}

# Auto-setup virtual environment if missing
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[*] Creating virtual environment (.venv)..." -ForegroundColor Cyan
    python -m venv .venv
    Write-Host "[*] Installing dependencies from requirements.txt..." -ForegroundColor Cyan
    & ".venv\Scripts\pip.exe" install -r requirements.txt
    Write-Host "[*] Setup complete!" -ForegroundColor Green
}

$env:PYTHONIOENCODING = "utf-8"
Write-Host "[*] Starting M.A.N.I. Desktop Assistant..." -ForegroundColor Green
& ".venv\Scripts\python.exe" run_jarvis.py

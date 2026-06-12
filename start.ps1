# Gridiron Prophet launcher (Windows / PowerShell)
# Usage:  powershell -ExecutionPolicy Bypass -File .\start.ps1

Write-Host "Starting Gridiron Prophet..." -ForegroundColor Cyan
Write-Host "================================"

Set-Location -Path $PSScriptRoot

# --- Virtual environment ---
if (-not (Test-Path "venv")) {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"

Write-Host "Checking dependencies..."
pip install -q -r requirements.txt

# --- Free port 8501 if something is already on it ---
$existing = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Freeing port 8501..."
    $existing | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

if (-not $env:GRIDIRON_ACCESS_PASSWORD) {
    Write-Host "WARNING: GRIDIRON_ACCESS_PASSWORD is not set - the app will refuse to load until you set it (e.g. in config/.env)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "Launching Streamlit + ngrok..." -ForegroundColor Green
Write-Host "================================"

# Streamlit in the background, ngrok in the foreground.
$streamlit = Start-Process -FilePath "streamlit" -ArgumentList "run", "streamlit_app.py" -PassThru -NoNewWindow
Start-Sleep -Seconds 5

try {
    python start_ngrok.py
}
finally {
    if ($streamlit -and -not $streamlit.HasExited) {
        Stop-Process -Id $streamlit.Id -Force -ErrorAction SilentlyContinue
    }
}

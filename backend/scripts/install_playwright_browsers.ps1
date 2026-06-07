# Installs Playwright Chromium with extended timeout, stale-lock cleanup,
# and a manual downloader fallback for slow/unreliable networks.
#
# Usage (from backend folder):
#   .\scripts\install_playwright_browsers.ps1

$ErrorActionPreference = "Stop"

$BackendRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"
$ManualDownloader = Join-Path $PSScriptRoot "manual_download_playwright.py"
$LockPath = Join-Path $env:LOCALAPPDATA "ms-playwright\__dirlock"

if (-not (Test-Path $Python)) {
    Write-Error "Virtual env not found. Run: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# 30-minute connection timeout (default is 30s, too short for large browser downloads)
$env:PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT = "1800000"

if (Test-Path $LockPath) {
    Write-Host "Removing stale Playwright lock: $LockPath"
    Remove-Item -Recurse -Force $LockPath
}

Write-Host "Attempting standard Playwright install..."
& $Python -m playwright install chromium
if ($LASTEXITCODE -eq 0) {
    Write-Host "Chromium installed successfully via Playwright CLI."
    exit 0
}

Write-Host "Standard install failed. Trying manual downloader fallback..."
& $Python $ManualDownloader --artifact all --timeout-seconds 3600
if ($LASTEXITCODE -eq 0) {
    Write-Host "Chromium installed successfully via manual downloader."
    exit 0
}

Write-Host ""
Write-Host "Browser download still failed."
Write-Host "The app can still run using installed Google Chrome or Microsoft Edge."
Write-Host "Set this in backend/.env:"
Write-Host "  BROWSER_CHANNEL=chrome"
Write-Host ""
exit 1

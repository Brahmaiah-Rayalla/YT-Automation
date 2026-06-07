# Build frontend (optional) and start the unified app server.
param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$BackendRoot = $PSScriptRoot
$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"
$BuildScript = Join-Path $BackendRoot "scripts\build_app.ps1"

if (-not (Test-Path $Python)) {
    Write-Error "Virtual env not found. Run: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}

function Stop-PortListeners {
    param([int]$Port)
    $connections = netstat -ano | Select-String "LISTENING" | Select-String ":$Port\s"
    $processIds = @()
    foreach ($line in $connections) {
        $parts = ($line.ToString() -split "\s+") | Where-Object { $_ -ne "" }
        if ($parts.Length -ge 5) {
            $processIds += [int]$parts[-1]
        }
    }
    foreach ($processId in ($processIds | Select-Object -Unique)) {
        if ($processId -gt 0) {
            Write-Host "Stopping existing process on port $Port (PID $processId)..."
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
}

Stop-PortListeners -Port 8000
Start-Sleep -Seconds 1

if (-not $SkipBuild) {
    & $BuildScript
}

Write-Host "Starting app at http://localhost:8000"
& $Python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

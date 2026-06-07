# Build frontend and copy into backend/static for single-app deployment.
$ErrorActionPreference = "Stop"

$BackendRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path (Split-Path -Parent $BackendRoot) "frontend"
$StaticDir = Join-Path $BackendRoot "static"

if (-not (Test-Path (Join-Path $FrontendRoot "package.json"))) {
    Write-Error "Frontend project not found at $FrontendRoot"
    exit 1
}

Push-Location $FrontendRoot
try {
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npm run build
} finally {
    Pop-Location
}

if (Test-Path $StaticDir) {
    Remove-Item -Recurse -Force $StaticDir
}
Copy-Item -Recurse (Join-Path $FrontendRoot "dist") $StaticDir
Write-Host "Built frontend into $StaticDir"

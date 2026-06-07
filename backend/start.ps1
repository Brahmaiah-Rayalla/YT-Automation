# Start the FastAPI backend using the project virtual environment.
$BackendRoot = $PSScriptRoot
$Python = Join-Path $BackendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Error "Virtual env not found. Run: python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}

& $Python -m uvicorn app.main:app --reload --port 8000

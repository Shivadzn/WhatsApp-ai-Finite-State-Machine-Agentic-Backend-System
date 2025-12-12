# Start Celery Worker Script
# Run this in a separate terminal

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Starting Celery Worker" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .\_venv\Scripts\Activate.ps1
}

Write-Host "Starting Celery worker..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Start Celery worker
# -A tasks: Application name
# -l info: Log level
# -P solo: Pool type (solo for Windows)
# -Q default,state: Listen to both queues
celery -A tasks worker -l info -P solo -Q default,state

Write-Host ""
Write-Host "Celery worker stopped." -ForegroundColor Yellow

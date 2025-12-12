# Simple Celery Status Check

Write-Host "========================================="
Write-Host "  Celery Status Check"
Write-Host "========================================="
Write-Host ""

# Check health endpoint
Write-Host "Checking Celery workers..."
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method GET
    Write-Host "Server: $($health.status)"
    Write-Host "Database: $($health.checks.database)"
    Write-Host "Redis: $($health.checks.redis)"
    Write-Host "Celery: $($health.checks.celery)"
    Write-Host ""
    
    if ($health.checks.celery -eq "no workers detected") {
        Write-Host "STATUS: Celery workers are NOT running" -ForegroundColor Red
        Write-Host ""
        Write-Host "Impact:"
        Write-Host "  - AI conversation state updates are queued but not processed"
        Write-Host "  - Operator messages won't sync to AI memory"
        Write-Host "  - Buffered messages won't be processed"
        Write-Host "  - Background tasks are accumulating in Redis"
        Write-Host ""
        Write-Host "To start Celery workers:"
        Write-Host "  1. Open a NEW PowerShell terminal"
        Write-Host "  2. Navigate to: cd C:\Users\KANCHAN\ai-backend"
        Write-Host "  3. Activate venv: .\_venv\Scripts\Activate.ps1"
        Write-Host "  4. Run: celery -A tasks worker -l info -P solo -Q default,state"
        Write-Host "  5. Keep that terminal open"
        Write-Host ""
    } else {
        Write-Host "STATUS: Celery workers are RUNNING" -ForegroundColor Green
        Write-Host "All background tasks are being processed!"
    }
} catch {
    Write-Host "ERROR: Cannot connect to server" -ForegroundColor Red
}

Write-Host "========================================="

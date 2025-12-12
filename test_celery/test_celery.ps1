# Celery Testing Script
# Tests if Celery workers are running and processing tasks

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Celery Status Check" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check health endpoint
Write-Host "Test 1: Health Check (Celery Status)" -ForegroundColor Green
Write-Host "------------------------------------"
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method GET
    Write-Host "Server Status: $($health.status)"
    Write-Host "Database: $($health.checks.database)"
    Write-Host "Redis: $($health.checks.redis)"
    
    if ($health.checks.celery -eq "no workers detected") {
        Write-Host "Celery: NO WORKERS DETECTED" -ForegroundColor Red
        Write-Host ""
        Write-Host "⚠️  Celery workers are not running!" -ForegroundColor Yellow
        Write-Host "   To start Celery, run in a separate terminal:" -ForegroundColor Yellow
        Write-Host "   .\start_celery.ps1" -ForegroundColor Cyan
        Write-Host ""
    } else {
        Write-Host "Celery: $($health.checks.celery)" -ForegroundColor Green
    }
} catch {
    Write-Host "ERROR: Cannot connect to server" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 2: Queue a task and check if it processes
Write-Host "Test 2: Task Processing Test" -ForegroundColor Green
Write-Host "----------------------------"
Write-Host "Sending operator message (queues Celery task)..."

$baseUrl = "http://localhost:5000/api/v1"
$payload = '{"phone":"919876543210","message":"Celery test message","messageId":null,"media":null}'

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "✅ Message queued: $($response.status)"
    Write-Host "   Message ID: $($response.message_id)"
    Write-Host ""
    Write-Host "📝 Note: Check server logs to see if Celery processes the task" -ForegroundColor Yellow
    Write-Host "   Look for: [Celery-...] Syncing operator message to graph" -ForegroundColor Gray
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: Check Redis for queued tasks
Write-Host "Test 3: Redis Queue Check" -ForegroundColor Green
Write-Host "-------------------------"
Write-Host "This requires redis-cli to be installed." -ForegroundColor Gray
Write-Host "To manually check Redis:" -ForegroundColor Yellow
Write-Host "  redis-cli -h localhost -p 6379" -ForegroundColor Cyan
Write-Host "  LLEN celery" -ForegroundColor Cyan
Write-Host "  LLEN state" -ForegroundColor Cyan
Write-Host ""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Celery Workers Status:" -ForegroundColor Yellow

if ($health.checks.celery -eq "no workers detected") {
    Write-Host "  ❌ NOT RUNNING" -ForegroundColor Red
    Write-Host ""
    Write-Host "Impact:" -ForegroundColor Yellow
    Write-Host "  • AI conversation state won't update" -ForegroundColor White
    Write-Host "  • Operator messages won't sync to AI memory" -ForegroundColor White
    Write-Host "  • Buffered messages won't process" -ForegroundColor White
    Write-Host "  • Message status updates won't work" -ForegroundColor White
    Write-Host ""
    Write-Host "To fix:" -ForegroundColor Green
    Write-Host "  1. Open a NEW terminal" -ForegroundColor White
    Write-Host "  2. Run: .\start_celery.ps1" -ForegroundColor Cyan
    Write-Host "  3. Keep it running in the background" -ForegroundColor White
} else {
    Write-Host "  ✅ RUNNING" -ForegroundColor Green
    Write-Host ""
    Write-Host "All background tasks are being processed!" -ForegroundColor Green
}
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan

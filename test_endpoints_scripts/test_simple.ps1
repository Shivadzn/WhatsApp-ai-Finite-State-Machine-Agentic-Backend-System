# Simple Operator Test Script
# Works reliably without special characters

$baseUrl = "http://localhost:5000/api/v1"
$testPhone = "919876543210"

Write-Host "========================================="
Write-Host "  Operator Endpoints Test"
Write-Host "========================================="
Write-Host ""

# Check server
Write-Host "Checking server..."
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method GET
    Write-Host "Server is running: $($health.status)"
    Write-Host ""
} catch {
    Write-Host "ERROR: Server is not running!"
    Write-Host "Please run: python run_server.py"
    exit 1
}

# Test 1: Takeover
Write-Host "Test 1: Takeover"
Write-Host "----------------"
$payload1 = '{"phone":"919876543210"}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/takeover" -Method POST -Body $payload1 -ContentType "application/json"
    Write-Host "PASS - Status: $($response.status)"
} catch {
    Write-Host "FAIL - Error: $($_.Exception.Message)"
}
Write-Host ""
Start-Sleep -Seconds 1

# Test 2: Send Operator Message
Write-Host "Test 2: Send Operator Message"
Write-Host "------------------------------"
$payload2 = '{"phone":"919876543210","message":"Test message from operator","messageId":null,"media":null}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload2 -ContentType "application/json"
    Write-Host "PASS - Status: $($response.status)"
    Write-Host "Message ID: $($response.message_id)"
} catch {
    Write-Host "FAIL - Error: $($_.Exception.Message)"
    if ($_.ErrorDetails.Message) {
        Write-Host "Details: $($_.ErrorDetails.Message)"
    }
}
Write-Host ""
Start-Sleep -Seconds 1

# Test 3: Handback
Write-Host "Test 3: Handback to AI"
Write-Host "----------------------"
$payload3 = '{"phone":"919876543210"}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/handback" -Method POST -Body $payload3 -ContentType "application/json"
    Write-Host "PASS - Status: $($response.status)"
} catch {
    Write-Host "FAIL - Error: $($_.Exception.Message)"
}
Write-Host ""
Start-Sleep -Seconds 1

# Test 4: Stats
Write-Host "Test 4: System Stats"
Write-Host "--------------------"
try {
    $stats = Invoke-RestMethod -Uri "http://localhost:5000/stats" -Method GET
    Write-Host "PASS - Active Buffers: $($stats.buffer.active_buffers)"
    Write-Host "Cache Type: $($stats.deduplication.cache_type)"
} catch {
    Write-Host "FAIL - Error: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "========================================="
Write-Host "Tests Complete!"
Write-Host "========================================="

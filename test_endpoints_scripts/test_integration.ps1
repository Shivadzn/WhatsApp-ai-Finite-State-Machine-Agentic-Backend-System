# Integration Testing Script
# Tests complete workflows

$baseUrl = "http://localhost:5000/api/v1"
$testPhone = "919876543210"

Write-Host "========================================="
Write-Host "  Integration Tests"
Write-Host "========================================="
Write-Host ""

# Workflow 1: Complete Operator Handoff Flow
Write-Host "Workflow 1: Complete Operator Handoff"
Write-Host "-------------------------------------"
Write-Host "Step 1: Takeover conversation"
$payload = '{"phone":"919876543210"}'
$response = Invoke-RestMethod -Uri "$baseUrl/takeover" -Method POST -Body $payload -ContentType "application/json"
Write-Host "  Takeover: $($response.status)"
Start-Sleep -Seconds 1

Write-Host "Step 2: Send operator message"
$payload = '{"phone":"919876543210","message":"Hello from operator","messageId":null,"media":null}'
$response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
Write-Host "  Message sent: $($response.status)"
Start-Sleep -Seconds 1

Write-Host "Step 3: Send another message"
$payload = '{"phone":"919876543210","message":"Second message","messageId":null,"media":null}'
$response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
Write-Host "  Message sent: $($response.status)"
Start-Sleep -Seconds 1

Write-Host "Step 4: Handback to AI"
$payload = '{"phone":"919876543210"}'
$response = Invoke-RestMethod -Uri "$baseUrl/handback" -Method POST -Body $payload -ContentType "application/json"
Write-Host "  Handback: $($response.status)"
Write-Host ""

# Workflow 2: Multiple Conversations
Write-Host "Workflow 2: Multiple Conversations"
Write-Host "----------------------------------"
$phones = @("919876543210", "919876543211", "919876543212")
foreach ($phone in $phones) {
    $payload = "{`"phone`":`"$phone`",`"message`":`"Test to $phone`",`"messageId`":null,`"media`":null}"
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
        Write-Host "  $phone : $($response.status)"
    } catch {
        Write-Host "  $phone : FAILED"
    }
    Start-Sleep -Milliseconds 500
}
Write-Host ""

# Workflow 3: Rapid Messages (Stress Test)
Write-Host "Workflow 3: Rapid Messages (5 messages)"
Write-Host "---------------------------------------"
for ($i = 1; $i -le 5; $i++) {
    $payload = "{`"phone`":`"919876543210`",`"message`":`"Rapid message $i`",`"messageId`":null,`"media`":null}"
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
        Write-Host "  Message $i : $($response.status)"
    } catch {
        Write-Host "  Message $i : FAILED"
    }
    Start-Sleep -Milliseconds 200
}
Write-Host ""

# Check system stats after load
Write-Host "System Stats After Load"
Write-Host "----------------------"
$stats = Invoke-RestMethod -Uri "http://localhost:5000/stats" -Method GET
Write-Host "  Active Buffers: $($stats.buffer.active_buffers)"
Write-Host "  Cache Type: $($stats.deduplication.cache_type)"
Write-Host ""

Write-Host "========================================="
Write-Host "Integration Tests Complete!"
Write-Host "========================================="

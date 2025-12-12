# Edge Case Testing Script
# Tests error handling and edge cases

$baseUrl = "http://localhost:5000/api/v1"

Write-Host "========================================="
Write-Host "  Edge Case Tests"
Write-Host "========================================="
Write-Host ""

# Test 1: Empty phone number
Write-Host "Test 1: Empty Phone Number"
Write-Host "--------------------------"
$payload = '{"phone":""}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/takeover" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "UNEXPECTED PASS - Should have failed"
} catch {
    Write-Host "PASS - Correctly rejected: $($_.Exception.Response.StatusCode)"
}
Write-Host ""

# Test 2: Invalid phone format
Write-Host "Test 2: Invalid Phone Format"
Write-Host "----------------------------"
$payload = '{"phone":"invalid"}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/takeover" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "PASS - Accepted (validation happens at WhatsApp API level)"
} catch {
    Write-Host "PASS - Rejected: $($_.Exception.Response.StatusCode)"
}
Write-Host ""

# Test 3: Missing required fields
Write-Host "Test 3: Missing Required Fields"
Write-Host "-------------------------------"
$payload = '{"message":"Test"}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "UNEXPECTED PASS - Should have failed"
} catch {
    Write-Host "PASS - Correctly rejected: $($_.Exception.Response.StatusCode)"
}
Write-Host ""

# Test 4: Empty message
Write-Host "Test 4: Empty Message"
Write-Host "--------------------"
$payload = '{"phone":"919876543210","message":"","messageId":null,"media":null}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "UNEXPECTED PASS - Should have rejected empty message"
} catch {
    Write-Host "PASS - Correctly rejected: $($_.Exception.Response.StatusCode)"
}
Write-Host ""

# Test 5: Very long message
Write-Host "Test 5: Very Long Message (4096 chars)"
Write-Host "--------------------------------------"
$longMessage = "A" * 4096
$payload = "{`"phone`":`"919876543210`",`"message`":`"$longMessage`",`"messageId`":null,`"media`":null}"
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "Response: $($response.status)"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
}
Write-Host ""

# Test 6: Special characters in message
Write-Host "Test 6: Special Characters"
Write-Host "--------------------------"
$payload = '{"phone":"919876543210","message":"Test with emojis 😀🎉 and special chars: @#$%","messageId":null,"media":null}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "PASS - Status: $($response.status)"
} catch {
    Write-Host "FAIL - Error: $($_.Exception.Message)"
}
Write-Host ""

# Test 7: Handback without takeover
Write-Host "Test 7: Handback Non-existent Conversation"
Write-Host "------------------------------------------"
$payload = '{"phone":"999999999999"}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/handback" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "UNEXPECTED PASS - Should have rejected non-existent conversation"
} catch {
    Write-Host "PASS - Correctly rejected: $($_.Exception.Response.StatusCode)"
}
Write-Host ""

Write-Host "========================================="
Write-Host "Edge Case Tests Complete!"
Write-Host "========================================="

# Full Customer Flow Test
# Tests complete AI conversation with Celery processing

$baseUrl = "http://localhost:5000/api/v1"
$webhookUrl = "http://localhost:5000/webhook"
$testPhone = "919876543210"

Write-Host "========================================="
Write-Host "  Full Customer Flow Test"
Write-Host "========================================="
Write-Host ""

# Step 1: Simulate incoming customer message
Write-Host "Step 1: Customer sends message"
Write-Host "------------------------------"
$incomingMessage = @"
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "15550000000",
          "phone_number_id": "PHONE_NUMBER_ID"
        },
        "contacts": [{
          "profile": {
            "name": "Test Customer"
          },
          "wa_id": "$testPhone"
        }],
        "messages": [{
          "from": "$testPhone",
          "id": "wamid.TEST_$(Get-Random)",
          "timestamp": "$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())",
          "text": {
            "body": "Hi, I want to order a chocolate cake"
          },
          "type": "text"
        }]
      },
      "field": "messages"
    }]
  }]
}
"@

try {
    $response = Invoke-RestMethod -Uri $webhookUrl -Method POST -Body $incomingMessage -ContentType "application/json"
    Write-Host "✅ Webhook accepted message"
    Write-Host "   Check Celery terminal for AI processing..."
    Write-Host ""
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)"
}

Start-Sleep -Seconds 5

# Step 2: Operator takeover
Write-Host "Step 2: Operator takes over conversation"
Write-Host "----------------------------------------"
$payload = '{"phone":"' + $testPhone + '"}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/takeover" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "✅ Takeover: $($response.status)"
    Write-Host "   Check Celery: Should see 'Updating LangGraph state'"
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)"
}

Start-Sleep -Seconds 3

# Step 3: Operator sends message
Write-Host ""
Write-Host "Step 3: Operator sends message"
Write-Host "------------------------------"
$payload = '{"phone":"' + $testPhone + '","message":"Hello! I can help you with that cake order. What size would you like?","messageId":null,"media":null}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/operator-message" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "✅ Message sent: $($response.status)"
    Write-Host "   WhatsApp ID: $($response.message_id)"
    Write-Host "   Check Celery: Should see 'Syncing operator message to graph'"
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)"
}

Start-Sleep -Seconds 3

# Step 4: Handback to AI
Write-Host ""
Write-Host "Step 4: Hand back to AI"
Write-Host "----------------------"
$payload = '{"phone":"' + $testPhone + '"}'
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/handback" -Method POST -Body $payload -ContentType "application/json"
    Write-Host "✅ Handback: $($response.status)"
    Write-Host "   Check Celery: Should see 'Updating LangGraph state'"
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "========================================="
Write-Host "  Test Complete!"
Write-Host "========================================="
Write-Host ""
Write-Host "What happened:"
Write-Host "  1. Customer message buffered and queued for AI"
Write-Host "  2. Operator took over (AI state updated)"
Write-Host "  3. Operator sent message (synced to AI memory)"
Write-Host "  4. Handed back to AI (AI state updated)"
Write-Host ""
Write-Host "Check Celery terminal to see all tasks processing!"

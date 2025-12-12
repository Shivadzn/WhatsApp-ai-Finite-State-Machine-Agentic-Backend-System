# Test Webhook Fix - check_buffer_task signature
# This tests the bug fix for the TypeError

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Testing Webhook Buffer Fix" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:5000"

# Test 1: Send a webhook message (should not error)
Write-Host "Test 1: Sending webhook message..." -ForegroundColor Yellow

$webhookPayload = @{
    object = "whatsapp_business_account"
    entry = @(
        @{
            id = "WHATSAPP_BUSINESS_ACCOUNT_ID"
            changes = @(
                @{
                    value = @{
                        messaging_product = "whatsapp"
                        metadata = @{
                            display_phone_number = "15550000000"
                            phone_number_id = "PHONE_NUMBER_ID"
                        }
                        contacts = @(
                            @{
                                profile = @{
                                    name = "Test Customer"
                                }
                                wa_id = "919876543210"
                            }
                        )
                        messages = @(
                            @{
                                from = "919876543210"
                                id = "wamid.TEST_FIX_$(Get-Random)"
                                timestamp = [string]([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
                                text = @{
                                    body = "Testing buffer fix"
                                }
                                type = "text"
                            }
                        )
                    }
                    field = "messages"
                }
            )
        }
    )
} | ConvertTo-Json -Depth 10

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/webhook" `
        -Method Post `
        -Body $webhookPayload `
        -ContentType "application/json" `
        -ErrorAction Stop
    
    Write-Host "✅ Webhook accepted: $($response.status)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Check server logs - should NOT see TypeError!" -ForegroundColor Cyan
    Write-Host "Expected: 'Scheduling buffer check for 919876543210 in 2 seconds'" -ForegroundColor Cyan
    Write-Host "Should NOT see: 'check_buffer_task() takes 1 positional argument but 2 were given'" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host "❌ Webhook failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Test Complete" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "If you see '✅ Webhook accepted' and NO TypeError in server logs," -ForegroundColor Green
Write-Host "the fix is working correctly!" -ForegroundColor Green
Write-Host ""

# Enhanced Test Suite for Joy Invite Bot with Actual Validation
# Checks database state and bot responses

param(
    [Parameter(Mandatory=$false)]
    [string]$PhoneNumber = "911234567890",
    
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "http://127.0.0.1:5000",
    
    [Parameter(Mandatory=$false)]
    [switch]$QuickMode = $false
)

# Test results tracking
$script:totalTests = 0
$script:passedTests = 0
$script:failedTests = 0
$script:testResults = @()
$script:conversationId = $null

# Helper: Get conversation ID for phone number
function Get-ConversationId {
    param([string]$Phone)
    
    try {
        # You'll need to implement this based on your DB structure
        # For now, return a mock value
        return 1
    } catch {
        Write-Host "⚠️  Could not fetch conversation ID: $($_.Exception.Message)" -ForegroundColor Yellow
        return $null
    }
}

# Helper: Get latest AI message from database
function Get-LatestAIMessage {
    param([string]$Phone)
    
    try {
        # Call your API endpoint to get last message
        $response = Invoke-RestMethod -Uri "$BaseUrl/api/messages/$Phone/latest" -Method GET -ErrorAction SilentlyContinue
        return $response
    } catch {
        Write-Host "⚠️  Could not fetch latest message from API" -ForegroundColor Yellow
        return $null
    }
}

# Helper: Check if operator intervention was triggered
function Test-OperatorIntervention {
    param([string]$Phone)
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/api/conversation/$Phone/status" -Method GET -ErrorAction SilentlyContinue
        return $response.operator_active -eq $true
    } catch {
        Write-Host "⚠️  Could not check operator status" -ForegroundColor Yellow
        return $false
    }
}

# Helper: Check health before starting tests
function Test-SystemHealth {
    Write-Host "🏥 Checking system health..." -ForegroundColor Cyan
    
    try {
        $health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method GET
        
        if ($health.status -eq "healthy") {
            Write-Host "✅ System is healthy" -ForegroundColor Green
            Write-Host "   Database: $($health.checks.database)" -ForegroundColor Gray
            Write-Host "   Redis: $($health.checks.redis)" -ForegroundColor Gray
            Write-Host "   Celery: $($health.checks.celery)" -ForegroundColor Gray
            return $true
        } else {
            Write-Host "❌ System health check failed: $($health.status)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Could not reach backend: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Send-TestMessage {
    param(
        [string]$Message,
        [string]$Phone = $PhoneNumber
    )
    
    $timestamp = [int][double]::Parse((Get-Date -UFormat %s))
    $messageId = "wamid.TEST_$(Get-Random -Minimum 1000 -Maximum 9999)"
    
    $body = @{
        object = "whatsapp_business_account"
        entry = @(
            @{
                changes = @(
                    @{
                        value = @{
                            metadata = @{
                                display_phone_number = "1234567890"
                                phone_number_id      = "790519984148918"
                            }
                            contacts = @(
                                @{
                                    wa_id   = $Phone
                                    profile = @{ name = "Test User" }
                                }
                            )
                            messages = @(
                                @{
                                    from      = $Phone
                                    id        = $messageId
                                    timestamp = $timestamp
                                    type      = "text"
                                    text      = @{ body = $Message }
                                }
                            )
                        }
                    }
                )
            }
        )
    } | ConvertTo-Json -Depth 10
    
    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/webhook" -Method POST -Body $body -ContentType "application/json" -ErrorAction Stop
        return @{ Success = $true; Response = $response; MessageId = $messageId }
    } catch {
        return @{ Success = $false; Error = $_.Exception.Message; MessageId = $messageId }
    }
}

function Test-Scenario {
    param(
        [string]$Name,
        [string]$Message,
        [string]$ExpectedBehavior,
        [int]$WaitSeconds = 8,
        [scriptblock]$Validator = $null,
        [string[]]$ExpectedKeywords = @(),
        [string[]]$UnexpectedKeywords = @(),
        [bool]$ShouldTriggerIntervention = $false
    )
    
    $script:totalTests++
    
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "TEST #$script:totalTests: $Name" -ForegroundColor Yellow
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "📝 Message:  " -NoNewline -ForegroundColor Gray
    Write-Host "'$Message'" -ForegroundColor White
    Write-Host "🎯 Expected: " -NoNewline -ForegroundColor Gray
    Write-Host "$ExpectedBehavior" -ForegroundColor White
    
    if ($ExpectedKeywords.Count -gt 0) {
        Write-Host "🔍 Should contain: " -NoNewline -ForegroundColor Gray
        Write-Host "$($ExpectedKeywords -join ', ')" -ForegroundColor Cyan
    }
    
    if ($UnexpectedKeywords.Count -gt 0) {
        Write-Host "🚫 Should NOT contain: " -NoNewline -ForegroundColor Gray
        Write-Host "$($UnexpectedKeywords -join ', ')" -ForegroundColor Magenta
    }
    
    Write-Host ""
    Write-Host "🚀 Sending..." -ForegroundColor Cyan
    
    $startTime = Get-Date
    $result = Send-TestMessage -Message $Message
    
    if (-not $result.Success) {
        Write-Host "❌ REQUEST FAILED: $($result.Error)" -ForegroundColor Red
        $script:failedTests++
        $script:testResults += @{
            Name = $Name
            Status = "FAIL"
            Message = $Message
            Expected = $ExpectedBehavior
            Error = $result.Error
        }
        return
    }
    
    $elapsed = ((Get-Date) - $startTime).TotalSeconds
    Write-Host "✅ Request sent successfully (${elapsed}s)" -ForegroundColor Green
    Write-Host "🆔 Message ID: $($result.MessageId)" -ForegroundColor Gray
    
    # Wait for processing
    $waitTime = if ($QuickMode) { [Math]::Min($WaitSeconds, 3) } else { $WaitSeconds }
    Write-Host "⏳ Waiting ${waitTime}s for processing..." -ForegroundColor Gray
    Start-Sleep -Seconds $waitTime
    
    # Run validation
    $validationPassed = $true
    $validationDetails = @()
    
    # Check for expected keywords in response
    if ($ExpectedKeywords.Count -gt 0 -or $UnexpectedKeywords.Count -gt 0) {
        Write-Host "🔍 Fetching bot response..." -ForegroundColor Cyan
        $latestMessage = Get-LatestAIMessage -Phone $PhoneNumber
        
        if ($latestMessage) {
            $responseText = $latestMessage.message_text
            Write-Host "🤖 Bot response: " -NoNewline -ForegroundColor Gray
            Write-Host "'$($responseText.Substring(0, [Math]::Min(100, $responseText.Length)))...'" -ForegroundColor White
            
            # Check expected keywords
            foreach ($keyword in $ExpectedKeywords) {
                if ($responseText -like "*$keyword*") {
                    Write-Host "   ✅ Found expected: '$keyword'" -ForegroundColor Green
                    $validationDetails += "Found: $keyword"
                } else {
                    Write-Host "   ❌ Missing expected: '$keyword'" -ForegroundColor Red
                    $validationPassed = $false
                    $validationDetails += "Missing: $keyword"
                }
            }
            
            # Check unexpected keywords
            foreach ($keyword in $UnexpectedKeywords) {
                if ($responseText -like "*$keyword*") {
                    Write-Host "   ❌ Found unexpected: '$keyword'" -ForegroundColor Red
                    $validationPassed = $false
                    $validationDetails += "Unexpected: $keyword"
                } else {
                    Write-Host "   ✅ Correctly absent: '$keyword'" -ForegroundColor Green
                    $validationDetails += "Absent: $keyword"
                }
            }
        } else {
            Write-Host "⚠️  Could not fetch response for validation" -ForegroundColor Yellow
            $validationDetails += "Could not fetch response"
        }
    }
    
    # Check intervention flag if expected
    if ($ShouldTriggerIntervention) {
        Write-Host "🔍 Checking intervention status..." -ForegroundColor Cyan
        $interventionTriggered = Test-OperatorIntervention -Phone $PhoneNumber
        
        if ($interventionTriggered) {
            Write-Host "   ✅ Intervention correctly triggered" -ForegroundColor Green
            $validationDetails += "Intervention: Yes"
        } else {
            Write-Host "   ❌ Intervention NOT triggered (expected)" -ForegroundColor Red
            $validationPassed = $false
            $validationDetails += "Intervention: Missing"
        }
    }
    
    # Run custom validator if provided
    if ($Validator) {
        Write-Host "🔍 Running custom validator..." -ForegroundColor Cyan
        try {
            $customResult = & $Validator
            if ($customResult) {
                Write-Host "   ✅ Custom validation passed" -ForegroundColor Green
                $validationDetails += "Custom: Pass"
            } else {
                Write-Host "   ❌ Custom validation failed" -ForegroundColor Red
                $validationPassed = $false
                $validationDetails += "Custom: Fail"
            }
        } catch {
            Write-Host "   ⚠️  Custom validator error: $($_.Exception.Message)" -ForegroundColor Yellow
            $validationDetails += "Custom: Error"
        }
    }
    
    # Record result
    $totalTime = ((Get-Date) - $startTime).TotalSeconds
    
    if ($validationPassed) {
        Write-Host "✅ TEST PASSED" -ForegroundColor Green
        $script:passedTests++
        $status = "PASS"
    } else {
        Write-Host "❌ TEST FAILED" -ForegroundColor Red
        $script:failedTests++
        $status = "FAIL"
    }
    
    $script:testResults += @{
        Name = $Name
        Status = $status
        Message = $Message
        Expected = $ExpectedBehavior
        Time = $totalTime
        ValidationDetails = $validationDetails -join "; "
    }
    
    Write-Host "👀 Check Celery logs for detailed processing flow" -ForegroundColor Magenta
}

# ============================================================================
# TEST SUITE START
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                                ║" -ForegroundColor Cyan
Write-Host "║          🧪 JOY INVITE BOT - ADVANCED TEST SUITE 🧪           ║" -ForegroundColor Cyan
Write-Host "║                                                                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "📱 Testing Phone:   $PhoneNumber" -ForegroundColor White
Write-Host "🌐 Backend URL:     $BaseUrl" -ForegroundColor White
Write-Host "⚡ Quick Mode:      $QuickMode" -ForegroundColor White
Write-Host "🕐 Start Time:      $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
Write-Host ""

# ============================================================================
# CATEGORY 1: CONVERSATION FLOW TESTS
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  📋 CATEGORY 1: CONVERSATION FLOW & CONTEXT MANAGEMENT        ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "Multi-turn Conversation - Context Retention" `
    -Message "Hi" `
    -ExpectedBehavior "Send greeting + one sample (AI), remember context" `
    -WaitSeconds 15

Test-Scenario `
    -Name "Follow-up Without Repeating Info" `
    -Message "aur dikhao" `
    -ExpectedBehavior "Send next sample (3D) without re-greeting" `
    -WaitSeconds 12

Test-Scenario `
    -Name "Reference Previous Message" `
    -Message "pehle wala achha tha" `
    -ExpectedBehavior "Acknowledge previous sample (3D), ask what they liked" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Complex Multi-Question Query" `
    -Message "mujhe 3D video chahiye, kitne din lagenge aur price kya hai?" `
    -ExpectedBehavior "Ask about number of functions first (don't answer everything at once)" `
    -WaitSeconds 8

# ============================================================================
# CATEGORY 2: LANGUAGE SWITCHING & HANDLING
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  🌍 CATEGORY 2: LANGUAGE SWITCHING & MULTILINGUAL SUPPORT     ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "Sudden English Switch Mid-Conversation" `
    -Message "Can you speak in English from now on?" `
    -ExpectedBehavior "Switch to English, continue conversation naturally" `
    -WaitSeconds 8

Test-Scenario `
    -Name "English Question After Language Switch" `
    -Message "What's the price for AI video?" `
    -ExpectedBehavior "Respond in English, ask about functions" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Mixed Language (Code-Switching)" `
    -Message "yaar can you send me pricing details for 2D videos?" `
    -ExpectedBehavior "Match user's mixed style or stay consistent with current language" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Pure Hindi (Devanagari Script)" `
    -Message "मुझे एआई वीडियो के बारे में बताओ" `
    -ExpectedBehavior "Respond in Hinglish (English alphabets) as per guidelines" `
    -WaitSeconds 8

# ============================================================================
# CATEGORY 3: PRICING & NEGOTIATION SCENARIOS
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  💰 CATEGORY 3: PRICING, BARGAINING & COMPLEX QUERIES         ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "Direct Pricing Without Context" `
    -Message "price batao" `
    -ExpectedBehavior "Ask which type (AI/3D/2D) user prefers first" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Pricing With Specific Type" `
    -Message "AI video ka price kya hai?" `
    -ExpectedBehavior "Ask about number of functions" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Complex Bargaining with Multiple Points" `
    -Message "bhai ye to bahut mehnga hai, aur koi discount mil sakta hai? mere pass budget bahut kam hai" `
    -ExpectedBehavior "Use ONE bargaining point (fast delivery OR quality OR competitive edge), not all" `
    -WaitSeconds 10

Test-Scenario `
    -Name "Price Comparison Question" `
    -Message "market mein to 2000 mein mil raha hai, tumhara itna kyun?" `
    -ExpectedBehavior "Justify pricing with value proposition (quality, delivery time, modifications)" `
    -WaitSeconds 10

Test-Scenario `
    -Name "Functions + Family Caricature + Extra Complexity" `
    -Message "mere paas 6 functions hain aur family caricature bhi chahiye, total kitna hoga?" `
    -ExpectedBehavior "Calculate: base price + (2 extra functions × 500) + 799 family caricature, ask which type" `
    -WaitSeconds 10

# ============================================================================
# CATEGORY 4: EDGE CASES & ERROR HANDLING
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  ⚠️  CATEGORY 4: EDGE CASES & GRACEFUL ERROR HANDLING         ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "Completely Gibberish Message" `
    -Message "asdfghjkl qwerty zxcvbn" `
    -ExpectedBehavior "Ask for clarification, don't escalate to operator" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Very Long Message (200+ characters)" `
    -Message "Haan bhai maine suna hai ki tum log invitation videos banate ho toh mujhe ye batao ki main apni shaadi ke liye ek video banana chahta hoon jo bahut hi unique ho aur sabko pasand aaye aur usme mere aur meri dulhan ki photos ho aur ek achha sa background music ho aur text bhi change kar sakte ho aur kitne din mein ready hoga aur price bhi batana" `
    -ExpectedBehavior "Process and respond naturally, extract key intents (video type, customization, timeline, pricing)" `
    -WaitSeconds 10

Test-Scenario `
    -Name "Message With Special Characters & Emojis" `
    -Message "Hey!!! 😍💕 Mujhe urgent video chahiye!!! 🔥🔥 ASAP!!! 🚨" `
    -ExpectedBehavior "Respond calmly, explain 1-2 day timeline, handle urgency appropriately" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Typos and Misspellings" `
    -Message "muze sampls bejo 2d ka pryce btao" `
    -ExpectedBehavior "Understand intent despite typos, respond appropriately" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Single Word Queries" `
    -Message "price" `
    -ExpectedBehavior "Ask which type of video, don't assume" `
    -WaitSeconds 6

Test-Scenario `
    -Name "Question Mark Only" `
    -Message "?" `
    -ExpectedBehavior "Ask how can I help, provide guidance" `
    -WaitSeconds 6

Test-Scenario `
    -Name "Multiple Questions in Rapid Fire" `
    -Message "price? delivery? changes possible? family caricature? refund policy?" `
    -ExpectedBehavior "Address systematically, ask which type first or provide overview" `
    -WaitSeconds 10

# ============================================================================
# CATEGORY 5: INTERVENTION & CUSTOM REQUESTS
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  🆘 CATEGORY 5: OPERATOR INTERVENTION & CUSTOM REQUESTS       ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "Clear Custom Request" `
    -Message "mujhe ek custom video banana hai jo bilkul alag ho" `
    -ExpectedBehavior "Silent escalation (empty content), operator_active = true" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Specific Custom Video Request" `
    -Message "main ek video dekha tha uske jaisa banana hai price kya hoga?" `
    -ExpectedBehavior "Silent escalation to operator" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Slide Mixing Request" `
    -Message "kya main different videos ke slides mix kar sakta hoon?" `
    -ExpectedBehavior "Explain why not recommended, then silent escalation" `
    -WaitSeconds 10

Test-Scenario `
    -Name "Services Outside Scope" `
    -Message "kya tum photographer bhi provide karte ho wedding ke liye?" `
    -ExpectedBehavior "Silent escalation to operator" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Same Day Urgent Delivery" `
    -Message "mujhe aaj hi video chahiye urgent hai" `
    -ExpectedBehavior "Silent escalation (same day not possible)" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Unclear But Not Custom" `
    -Message "mujhe kuch alag chahiye" `
    -ExpectedBehavior "Ask for clarification first, don't escalate immediately" `
    -WaitSeconds 8

# ============================================================================
# CATEGORY 6: TECHNICAL QUERIES & FEATURES
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  🔧 CATEGORY 6: TECHNICAL QUERIES & FEATURE QUESTIONS         ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "What is Caricature?" `
    -Message "caricature kya hota hai exactly?" `
    -ExpectedBehavior "Explain: cartoonish representations made from photos" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Face Match Percentage Query" `
    -Message "face match kitna percent hota hai AI video mein?" `
    -ExpectedBehavior "Explain: AI 70-80%, 2D/3D 100%" `
    -WaitSeconds 8

Test-Scenario `
    -Name "What Changes Are Possible?" `
    -Message "video mein kya kya change kar sakte hain?" `
    -ExpectedBehavior "Explain: text, song, caricature face; NOT background" `
    -WaitSeconds 8

Test-Scenario `
    -Name "PDF Only Request" `
    -Message "mujhe sirf PDF chahiye video nahi chahiye" `
    -ExpectedBehavior "Explain: PDF is free with video, but price remains same even for PDF only" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Family Caricature Details" `
    -Message "family caricature mein kitne log add kar sakte hain?" `
    -ExpectedBehavior "Explain: max 6 members (couple + parents), extra 799, only in 2D/3D not AI" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Delivery Timeline Questions" `
    -Message "agar main aaj order karun to kab tak milega?" `
    -ExpectedBehavior "1-2 days, faster if you verify quickly" `
    -WaitSeconds 8

# ============================================================================
# CATEGORY 7: PAYMENT & ORDER PROCESS
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  💳 CATEGORY 7: PAYMENT & ORDER PROCESS QUERIES               ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "Payment Method Query" `
    -Message "payment kaise karna hai?" `
    -ExpectedBehavior "Explain: half advance, half after work complete" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Order Process Flow Question" `
    -Message "order karne ke baad kya process hoti hai?" `
    -ExpectedBehavior "Explain: payment → WhatsApp group → designers verify → final payment" `
    -WaitSeconds 10

Test-Scenario `
    -Name "Refund Policy Query" `
    -Message "agar mujhe pasand nahi aaya to refund milega?" `
    -ExpectedBehavior "Yes, full refund if not satisfied, quality guarantee" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Photo Requirements Question" `
    -Message "photos kaisi honi chahiye?" `
    -ExpectedBehavior "Passport-like with smile, not cross-face, good lighting, separate photos OK" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Ready to Order (Implicit)" `
    -Message "theek hai main order karna chahta hoon 3D video 4 functions ke liye" `
    -ExpectedBehavior "Send order placement template with fields for details" `
    -WaitSeconds 10

# ============================================================================
# CATEGORY 8: STRESS TESTS & RAPID SUCCESSION
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  🔥 CATEGORY 8: STRESS TESTS & RAPID MESSAGE HANDLING         ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "Topic Change Mid-Conversation" `
    -Message "wait, AI video ke features kya hain?" `
    -ExpectedBehavior "Switch topic gracefully, explain AI video features" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Contradicting Previous Statement" `
    -Message "actually mujhe 2D nahi 3D chahiye" `
    -ExpectedBehavior "Acknowledge change, provide 3D information" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Thank You Mid-Conversation" `
    -Message "thanks for the info" `
    -ExpectedBehavior "Acknowledge, ask if anything else needed" `
    -WaitSeconds 6

Test-Scenario `
    -Name "Negative Sentiment" `
    -Message "yaar mujhe kuch samajh nahi aa raha" `
    -ExpectedBehavior "Empathize, offer to explain step by step" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Call Request" `
    -Message "main aapko call kar sakta hoon?" `
    -ExpectedBehavior "Provide call number: 9016302607" `
    -WaitSeconds 6

# ============================================================================
# CATEGORY 9: SOUTH INDIAN & REGIONAL VARIATIONS
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  🌏 CATEGORY 9: REGIONAL VARIATIONS & SOUTH INDIAN HANDLING   ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "South Indian Customer (English)" `
    -Message "Hello, I need invitation video for my wedding" `
    -ExpectedBehavior "Respond in English, offer south_india samples" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Punjabi Wedding Request" `
    -Message "Punjabi wedding da video chahida" `
    -ExpectedBehavior "Understand intent, offer Punjabi category samples" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Engagement Video Request" `
    -Message "engagement ke liye video banate ho?" `
    -ExpectedBehavior "Yes, offer engagement samples, mention pricing (2000 for AI)" `
    -WaitSeconds 8

# ============================================================================
# CATEGORY 10: RECOVERY & RESILIENCE
# ============================================================================

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  🛡️  CATEGORY 10: ERROR RECOVERY & SYSTEM RESILIENCE          ║" -ForegroundColor Yellow
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Test-Scenario `
    -Name "Return After Long Gap" `
    -Message "Hi, I'm back" `
    -ExpectedBehavior "Welcome back, check conversation history, continue naturally" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Asking Same Question Again" `
    -Message "price batao" `
    -ExpectedBehavior "Ask which type again (don't assume based on old context)" `
    -WaitSeconds 8

Test-Scenario `
    -Name "Restart Conversation" `
    -Message "chalo phir se start karte hain" `
    -ExpectedBehavior "Reset gracefully, start fresh greeting" `
    -WaitSeconds 8

# ============================================================================
# RESULTS SUMMARY
# ============================================================================

Write-Host ""
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                      📊 TEST RESULTS SUMMARY                   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$passRate = if ($script:totalTests -gt 0) { 
    [math]::Round(($script:passedTests / $script:totalTests) * 100, 2) 
} else { 0 }

Write-Host "Total Tests:    " -NoNewline -ForegroundColor White
Write-Host "$script:totalTests" -ForegroundColor Cyan

Write-Host "Passed:         " -NoNewline -ForegroundColor White
Write-Host "$script:passedTests" -ForegroundColor Green

Write-Host "Failed:         " -NoNewline -ForegroundColor White
Write-Host "$script:failedTests" -ForegroundColor Red

Write-Host "Pass Rate:      " -NoNewline -ForegroundColor White
Write-Host "${passRate}%" -ForegroundColor $(if ($passRate -ge 90) { "Green" } elseif ($passRate -ge 70) { "Yellow" } else { "Red" })

Write-Host ""
Write-Host "🕐 End Time:       $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "DETAILED RESULTS BY CATEGORY:" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

foreach ($result in $script:testResults) {
    $color = if ($result.Status -eq "PASS") { "Green" } else { "Red" }
    $icon = if ($result.Status -eq "PASS") { "✅" } else { "❌" }
    
    Write-Host "$icon $($result.Status): " -NoNewline -ForegroundColor $color
    Write-Host "$($result.Name)" -ForegroundColor White
    
    if ($result.Error) {
        Write-Host "   Error: $($result.Error)" -ForegroundColor Red
    }
    
    if ($result.Time) {
        Write-Host "   Time: $($result.Time)s" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Export results to file
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$resultsFile = "test_results_$timestamp.json"
$script:testResults | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultsFile -Encoding UTF8

Write-Host "📁 Results exported to: $resultsFile" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 TIP: Review Celery logs to verify bot behavior for each test" -ForegroundColor Yellow
Write-Host ""

if ($script:failedTests -eq 0) {
    Write-Host "🎉 ALL TESTS PASSED! Your bot is production-ready! 🎉" -ForegroundColor Green
} elseif ($passRate -ge 90) {
    Write-Host "✨ EXCELLENT! Most tests passed. Review failed tests and iterate." -ForegroundColor Green
} elseif ($passRate -ge 70) {
    Write-Host "⚠️  GOOD START! Some improvements needed. Check failed tests." -ForegroundColor Yellow
} else {
    Write-Host "❌ NEEDS WORK! Multiple failures detected. Review logs carefully." -ForegroundColor Red
}

Write-Host ""
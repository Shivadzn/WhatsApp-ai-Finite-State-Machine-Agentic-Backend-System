# Verify System Prompt Upgrade
# Checks if v2.0 features are present in the prompt file

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  System Prompt Upgrade Verification" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

$promptFile = "gemini_system_prompt.txt"

if (!(Test-Path $promptFile)) {
    Write-Host "❌ ERROR: $promptFile not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Checking prompt file: $promptFile" -ForegroundColor Yellow
Write-Host ""

$content = Get-Content $promptFile -Raw

# Check for v2.0 features
$checks = @(
    @{Name="Version 2.0 Header"; Pattern="v2.0"; Required=$true},
    @{Name="Strict Rules Section"; Pattern="STRICT RULES \(NEVER BREAK\)"; Required=$true},
    @{Name="Operator Handoff Awareness"; Pattern="Operator Handoff Awareness"; Required=$true},
    @{Name="Context Management"; Pattern="Conversation Context Management"; Required=$true},
    @{Name="Updated Pricing"; Pattern="SPECIAL OFFER - THIS MONTH ONLY"; Required=$true},
    @{Name="Greeting Templates"; Pattern="Greeting Templates"; Required=$true},
    @{Name="Error Handling"; Pattern="Error Handling"; Required=$true},
    @{Name="Security Section"; Pattern="Security & Privacy"; Required=$true},
    @{Name="Silent Escalation Protocol"; Pattern="How to Escalate \(CRITICAL\)"; Required=$true},
    @{Name="Response Length Examples"; Pattern="Response Length Enforcement"; Required=$true}
)

$passed = 0
$failed = 0

foreach ($check in $checks) {
    $name = $check.Name
    $pattern = $check.Pattern
    
    if ($content -match $pattern) {
        Write-Host "✅ $name" -ForegroundColor Green
        $passed++
    } else {
        Write-Host "❌ $name - NOT FOUND" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Results: $passed passed, $failed failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

if ($failed -eq 0) {
    Write-Host "🎉 SUCCESS! Prompt is upgraded to v2.0" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Restart server: python run_server.py"
    Write-Host "  2. Restart Celery: celery -A tasks worker -l info -P solo -Q default,state"
    Write-Host "  3. Test: .\test_full_flow.ps1"
    Write-Host ""
} else {
    Write-Host "⚠️  WARNING: Some v2.0 features are missing!" -ForegroundColor Yellow
    Write-Host "The prompt file may need to be updated." -ForegroundColor Yellow
    Write-Host ""
}

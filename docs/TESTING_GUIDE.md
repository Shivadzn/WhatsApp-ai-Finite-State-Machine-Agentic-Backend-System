# Testing Guide

## Overview
This guide covers all testing procedures for the AI WhatsApp Backend system.

---

## Prerequisites

### System Requirements
- FastAPI server running on `http://localhost:5000`
- Celery worker running
- PostgreSQL database accessible
- Redis server running
- Valid WhatsApp Business API credentials in `.env`

### Verify System is Ready
```powershell
.\check_celery.ps1
```

Expected output:
```
Server: healthy
Database: connected
Redis: connected
Celery: 1 workers active
```

---

## Test Scripts

### 1. Health Check (`check_celery.ps1`)

**Purpose**: Verify all system components are running

**Usage**:
```powershell
.\check_celery.ps1
```

**What it checks**:
- FastAPI server status
- Database connectivity
- Redis connectivity
- Celery worker status

**Expected Result**:
```
STATUS: Celery workers are RUNNING
All background tasks are being processed!
```

---

### 2. Full Customer Flow Test (`test_full_flow.ps1`)

**Purpose**: Test complete customer service workflow

**Usage**:
```powershell
.\test_full_flow.ps1
```

**Test Steps**:
1. **Customer Message**: Simulates incoming WhatsApp message
2. **Operator Takeover**: Operator takes control of conversation
3. **Operator Message**: Operator sends message to customer
4. **Handback**: Conversation handed back to AI

**Expected Results**:
```
✅ Webhook accepted message
✅ Takeover: takeover_complete
✅ Message sent: success
✅ Handback: handback_complete
```

**What to Watch in Celery Terminal**:
```
[INFO] Task tasks.check_buffer received
[INFO] Task tasks.update_langgraph_state received
[INFO] Task tasks.sync_operator_message_to_graph received
[INFO] All tasks succeeded
```

---

## Manual Testing

### Test 1: Operator Takeover

**Request**:
```powershell
$payload = '{"phone":"919876543210"}'
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/takeover" -Method POST -Body $payload -ContentType "application/json"
```

**Expected Response**:
```json
{
  "status": "takeover_complete"
}
```

**Verify**:
1. Check database: `human_intervention_required = TRUE`
2. Check Celery logs: "Updating LangGraph state"
3. Check LangGraph state: `operator_active = True`

---

### Test 2: Send Operator Message

**Request**:
```powershell
$payload = '{"phone":"919876543210","message":"Test message from operator","messageId":null,"media":null}'
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/operator-message" -Method POST -Body $payload -ContentType "application/json"
```

**Expected Response**:
```json
{
  "status": "success",
  "message": "Message queued for processing",
  "message_id": "wamid.HBgMOTE5ODc2NTQzMjEwFQIAERgS..."
}
```

**Verify**:
1. Message appears in WhatsApp
2. Message stored in database
3. Celery logs: "Syncing operator message to graph"
4. Message added to AI conversation history

---

### Test 3: Handback to AI

**Request**:
```powershell
$payload = '{"phone":"919876543210"}'
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/handback" -Method POST -Body $payload -ContentType "application/json"
```

**Expected Response**:
```json
{
  "status": "handback_complete"
}
```

**Verify**:
1. Check database: `human_intervention_required = FALSE`
2. Check Celery logs: "Updating LangGraph state"
3. Check LangGraph state: `operator_active = False`

---

## Edge Case Testing

### Test: Empty Message
```powershell
$payload = '{"phone":"919876543210","message":"","messageId":null,"media":null}'
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/operator-message" -Method POST -Body $payload -ContentType "application/json"
```

**Expected**: 400 Bad Request - "Message text or media is required"

---

### Test: Missing Phone Number
```powershell
$payload = '{"phone":"","message":"Test","messageId":null,"media":null}'
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/operator-message" -Method POST -Body $payload -ContentType "application/json"
```

**Expected**: 400 Bad Request - "Phone number is required"

---

### Test: Non-existent Conversation (Takeover)
```powershell
$payload = '{"phone":"999999999999"}'
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/takeover" -Method POST -Body $payload -ContentType "application/json"
```

**Expected**: 404 Not Found - "No conversation found for phone number"

---

### Test: Non-existent Conversation (Handback)
```powershell
$payload = '{"phone":"999999999999"}'
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/handback" -Method POST -Body $payload -ContentType "application/json"
```

**Expected**: 404 Not Found - "No conversation found for phone number"

---

### Test: Non-existent Conversation (Operator Message)
```powershell
$payload = '{"phone":"999999999999","message":"Test","messageId":null,"media":null}'
Invoke-RestMethod -Uri "http://localhost:5000/api/v1/operator-message" -Method POST -Body $payload -ContentType "application/json"
```

**Expected**: 200 OK - Creates new conversation automatically

---

## Database Verification

### Check Conversation State
```sql
SELECT phone, human_intervention_required, last_message_id, created_at 
FROM conversation 
WHERE phone = '919876543210';
```

### Check Messages
```sql
SELECT direction, sender_type, message_text, created_at 
FROM message 
WHERE conversation_id = (
  SELECT id FROM conversation WHERE phone = '919876543210'
)
ORDER BY created_at DESC 
LIMIT 10;
```

### Check LangGraph State
```sql
SELECT * FROM checkpoints 
WHERE thread_id = '919876543210' 
ORDER BY checkpoint_id DESC 
LIMIT 1;
```

---

## Performance Testing

### Test: Rapid Messages
Send 10 messages in quick succession:

```powershell
for ($i = 1; $i -le 10; $i++) {
    $payload = "{`"phone`":`"919876543210`",`"message`":`"Rapid message $i`",`"messageId`":null,`"media`":null}"
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/operator-message" -Method POST -Body $payload -ContentType "application/json"
    Start-Sleep -Milliseconds 100
}
```

**Expected**:
- All messages sent successfully
- All Celery tasks complete
- No errors in logs
- Messages appear in correct order

---

### Test: Multiple Conversations
```powershell
$phones = @("919876543210", "919876543211", "919876543212")
foreach ($phone in $phones) {
    $payload = "{`"phone`":`"$phone`",`"message`":`"Test to $phone`",`"messageId`":null,`"media`":null}"
    Invoke-RestMethod -Uri "http://localhost:5000/api/v1/operator-message" -Method POST -Body $payload -ContentType "application/json"
}
```

**Expected**:
- All messages sent successfully
- Separate conversations created for each phone
- Celery processes all tasks

---

## Webhook Testing

### Test: Incoming Message Webhook
```powershell
$webhook = "http://localhost:5000/webhook"
$payload = @"
{
  "object": "whatsapp_business_account",
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "from": "919876543210",
          "id": "wamid.TEST123",
          "timestamp": "1234567890",
          "text": {"body": "Hello"},
          "type": "text"
        }]
      }
    }]
  }]
}
"@

Invoke-RestMethod -Uri $webhook -Method POST -Body $payload -ContentType "application/json"
```

**Expected**:
- Webhook returns `{"status": "received"}`
- Message buffered in Redis
- Celery processes buffer after 2 seconds
- AI generates response (if not in operator mode)

---

## Troubleshooting Tests

### If Test Fails: Check Server Logs
Look for errors in the terminal running `python run_server.py`

### If Test Fails: Check Celery Logs
Look for task failures in the Celery worker terminal

### If Test Fails: Check Database
```sql
-- Check if conversation exists
SELECT * FROM conversation WHERE phone = '919876543210';

-- Check recent messages
SELECT * FROM message ORDER BY created_at DESC LIMIT 5;
```

### If Test Fails: Check Redis
```bash
redis-cli
KEYS *
GET buffer:919876543210
```

---

## Test Results Checklist

After running all tests, verify:

- [ ] Health check passes
- [ ] Takeover works (conversation state updates)
- [ ] Operator message sends (appears in WhatsApp)
- [ ] Operator message syncs to AI (Celery task completes)
- [ ] Handback works (conversation state updates)
- [ ] Edge cases handled correctly
- [ ] Database records created
- [ ] Celery tasks execute successfully
- [ ] No errors in server logs
- [ ] No errors in Celery logs

---

## Continuous Testing

### Daily Tests
```powershell
# Quick health check
.\check_celery.ps1
```

### Before Deployment
```powershell
# Full test suite
.\test_full_flow.ps1
```

### After Code Changes
1. Run health check
2. Run full flow test
3. Check Celery logs for errors
4. Verify database state

---

## Test Data Cleanup

### Clear Test Messages
```sql
DELETE FROM message 
WHERE conversation_id IN (
  SELECT id FROM conversation WHERE phone LIKE '91987654321%'
);
```

### Clear Test Conversations
```sql
DELETE FROM conversation WHERE phone LIKE '91987654321%';
```

### Clear Redis Test Data
```bash
redis-cli
FLUSHDB
```

---

## Automated Testing (Future)

Consider implementing:
- Unit tests with pytest
- Integration tests with pytest-asyncio
- API tests with httpx
- Load tests with locust
- CI/CD pipeline with GitHub Actions

---

## Success Criteria

A successful test run should show:
1. ✅ All API endpoints respond correctly
2. ✅ All Celery tasks execute without errors
3. ✅ Database records created accurately
4. ✅ WhatsApp messages sent successfully
5. ✅ AI conversation state synchronized
6. ✅ No memory leaks or performance issues
7. ✅ Error handling works as expected
8. ✅ Edge cases handled gracefully

---

## Contact

For testing issues or questions, refer to:
- `DOCUMENTATION.md` - System documentation
- `celery_production.md` - Celery-specific information
- Server logs - Runtime errors
- Celery logs - Task execution details

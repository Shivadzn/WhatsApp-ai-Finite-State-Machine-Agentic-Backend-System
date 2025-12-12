# System Prompt Upgrade Guide

## Overview

This guide explains the changes from `gemini_system_prompt.txt` (v1.0) to `gemini_system_prompt_v2.txt` (v2.0) and how to migrate.

---

## What Changed?

### ✅ Major Improvements

#### 1. **Operator Handoff Awareness** (NEW)
**Why**: AI needs to know when operator is active and what operator discussed.

**What's New**:
- Detects `[OPERATOR MESSAGE]:` in conversation history
- Stays silent when `operator_active = True`
- Reviews operator messages after handback
- Continues conversation with full context

**Impact**: Prevents AI from responding when operator is handling conversation.

---

#### 2. **Updated Pricing Template**
**Before**:
```
THIS PRICE OFFER IS VALID TILL 15 OCT
```

**After**:
```
🎉 SPECIAL OFFER - THIS MONTH ONLY
```

**Why**: Date was outdated (we're in November). New version is evergreen.

---

#### 3. **Conversation Context Management** (NEW)
**Why**: AI should remember what customer said and not ask same questions twice.

**What's New**:
- Tracks customer's video type preference
- Remembers number of functions
- Recalls language preference
- References previous answers

**Example**:
```
Customer: "3D video ka price?"
AI: "Kitne functions hain?" 
Customer: "4"
AI: [Sends pricing]

Later...
Customer: "Changes ho sakte hain?"
AI: "3D video mein text, song aur face change ho sakta hai."
     ↑ Remembered customer wants 3D
```

---

#### 4. **Greeting & Closing Templates** (NEW)
**Why**: Consistent, professional conversation flow.

**What's New**:
- First message greeting
- Returning customer greeting
- Order confirmation closing
- "Will think about it" response
- Not interested closing

---

#### 5. **Error Handling Section** (NEW)
**Why**: AI needs to handle failures gracefully.

**What's New**:
- Media send failure response
- WhatsApp API error response
- Unclear request handling
- Out of scope requests

---

#### 6. **Strengthened Human Intervention Protocol**
**Before**: Basic explanation

**After**: 
- Clear step-by-step instructions
- Examples of correct vs wrong escalation
- Emphasis on "silent" handoff
- No acknowledgment to customer

**Critical Change**:
```
❌ WRONG:
Customer: "Custom video?"
AI: "Ek minute, main connect karta hoon." [Call tool]

✅ CORRECT:
Customer: "Custom video?"
AI: [Call tool] [No message] [Stop responding]
```

---

#### 7. **Response Length Enforcement**
**Before**: "16-18 words maximum"

**After**: Examples of correct vs wrong responses

**Example**:
```
❌ Wrong (too long):
"Haan bilkul, hum 2D aur 3D videos banate hain with custom caricature faces and delivery 1-2 days mein."

✅ Correct (split):
"Haan bilkul! Hum 2D aur 3D videos banate hain."
"Custom caricature faces ke saath."
"Delivery 1-2 din mein."
```

---

#### 8. **Security & Privacy Section** (NEW)
**Why**: Protect customer data and business information.

**What's New**:
- What never to share
- How to respond if asked about AI
- How to handle personal info requests
- Customer privacy protection

---

#### 9. **Strict Rules Section** (NEW)
**Why**: Critical rules that AI must never break.

**What's New**:
- 5 non-negotiable rules at the top
- Easy for AI to reference
- Clear priority

---

### 📝 Minor Improvements

- Better formatting and structure
- More examples throughout
- Clearer section headings
- Version history added
- Improved readability

---

## Migration Steps

### Step 1: Backup Current Prompt
```bash
# Current file is already backed up as gemini_system_prompt.txt
# v2 is in gemini_system_prompt_v2.txt
```

### Step 2: Update bot.py to Use New Prompt

Open `bot.py` and change line 230:

**Before**:
```python
with open("gemini_system_prompt.txt", "r", encoding="utf-8") as f1:
```

**After**:
```python
with open("gemini_system_prompt_v2.txt", "r", encoding="utf-8") as f1:
```

Or simply rename the file:
```bash
# Backup old version
mv gemini_system_prompt.txt gemini_system_prompt_v1_backup.txt

# Use new version
mv gemini_system_prompt_v2.txt gemini_system_prompt.txt
```

### Step 3: Restart Server and Celery

```bash
# Stop server (Ctrl+C in server terminal)
# Stop Celery (Ctrl+C in Celery terminal)

# Restart server
python run_server.py

# Restart Celery
celery -A tasks worker -l info -P solo -Q default,state
```

### Step 4: Test the Changes

```bash
# Run health check
.\check_celery.ps1

# Test full flow
.\test_full_flow.ps1
```

### Step 5: Monitor AI Responses

Watch for:
- ✅ Shorter responses (16-18 words)
- ✅ AI stays silent when operator is active
- ✅ AI references operator messages after handback
- ✅ No repeated questions
- ✅ Silent escalation (no "let me connect you" messages)

---

## Comparison Table

| Feature | v1.0 (Old) | v2.0 (New) |
|---------|-----------|-----------|
| **Operator Awareness** | ❌ No | ✅ Yes - detects and respects operator mode |
| **Context Memory** | ❌ Basic | ✅ Advanced - remembers preferences |
| **Pricing Date** | ❌ Outdated (Oct 15) | ✅ Evergreen (This Month) |
| **Greeting Templates** | ❌ No | ✅ Yes - multiple scenarios |
| **Error Handling** | ❌ No | ✅ Yes - graceful failures |
| **Escalation Protocol** | ⚠️ Basic | ✅ Detailed with examples |
| **Response Length** | ⚠️ Rule only | ✅ Rule + examples |
| **Security Section** | ❌ No | ✅ Yes - privacy protection |
| **Strict Rules** | ⚠️ Scattered | ✅ Consolidated at top |
| **Version Control** | ❌ No | ✅ Yes - version history |

---

## Testing Checklist

After migration, test these scenarios:

### ✅ Operator Handoff Test
1. Customer sends message
2. Operator takes over
3. Operator sends message
4. **Verify**: AI doesn't respond while operator is active
5. Operator hands back
6. Customer sends message
7. **Verify**: AI responds and references operator's message

### ✅ Context Memory Test
1. Customer: "3D video ka price?"
2. AI asks: "Kitne functions?"
3. Customer: "4"
4. AI sends pricing
5. Later, customer: "Changes ho sakte hain?"
6. **Verify**: AI mentions "3D video mein..." (remembered type)

### ✅ Response Length Test
1. Ask complex question
2. **Verify**: AI splits response into multiple short messages
3. Each message should be 16-18 words max

### ✅ Silent Escalation Test
1. Customer: "Custom video ban sakta hai?"
2. **Verify**: AI calls RequestIntervention tool
3. **Verify**: AI sends NO message to customer
4. **Verify**: AI stops responding

### ✅ Greeting Test
1. New customer sends "Hi"
2. **Verify**: AI sends proper greeting
3. **Verify**: AI sends samples in correct order

### ✅ Error Handling Test
1. Simulate media send failure
2. **Verify**: AI responds with error message
3. **Verify**: AI offers to retry

---

## Rollback Plan

If v2.0 causes issues:

### Quick Rollback
```bash
# Restore old version
mv gemini_system_prompt_v1_backup.txt gemini_system_prompt.txt

# Restart
python run_server.py  # In terminal 1
celery -A tasks worker -l info -P solo -Q default,state  # In terminal 2
```

### Gradual Rollback
Keep both versions and switch based on testing:
```python
# In bot.py, add version selector
USE_V2 = False  # Set to True to use v2

prompt_file = "gemini_system_prompt_v2.txt" if USE_V2 else "gemini_system_prompt.txt"
with open(prompt_file, "r", encoding="utf-8") as f1:
    GEMINI_SYSTEM_PROMPT = f1.read()
```

---

## Expected Improvements

### 1. Better Operator Handoff
**Before**: AI might respond when operator is active  
**After**: AI stays completely silent during operator mode

### 2. Smarter Conversations
**Before**: AI asks same questions multiple times  
**After**: AI remembers context and builds on it

### 3. Cleaner Escalations
**Before**: "Ek minute, main connect karta hoon"  
**After**: Silent handoff, no customer-facing message

### 4. More Professional
**Before**: Inconsistent greetings  
**After**: Proper greetings and closings

### 5. Better Error Handling
**Before**: No response on errors  
**After**: Graceful error messages

---

## Monitoring Metrics

Track these after migration:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Avg Response Length** | 16-18 words | Check conversation logs |
| **Operator Conflicts** | 0 | AI responding during operator mode |
| **Repeated Questions** | <5% | Same question asked twice |
| **Escalation Messages** | 0 | "Let me connect you" messages |
| **Context Retention** | >90% | AI remembers previous answers |

---

## FAQ

### Q: Do I need to retrain the AI?
**A**: No, this is just a prompt update. No retraining needed.

### Q: Will existing conversations break?
**A**: No, the AI will continue existing conversations with new rules.

### Q: Can I use both versions?
**A**: Yes, you can switch between them for testing.

### Q: How long does migration take?
**A**: 5-10 minutes (file rename + restart)

### Q: Will customers notice the change?
**A**: They'll notice better responses, shorter messages, and smoother handoffs.

### Q: What if something breaks?
**A**: Use the rollback plan above to restore v1.0 immediately.

---

## Support

If you encounter issues after migration:

1. Check server logs for errors
2. Check Celery logs for task failures
3. Verify prompt file is loaded correctly
4. Test with `.\test_full_flow.ps1`
5. Rollback if needed

---

## Next Steps

After successful migration:

1. ✅ Monitor AI responses for 24 hours
2. ✅ Collect customer feedback
3. ✅ Fine-tune if needed
4. ✅ Update documentation
5. ✅ Train team on new features

---

## Version History

**v2.0** - Current
- Major improvements to operator handoff
- Context management
- Error handling
- Security section

**v1.0** - Previous
- Initial system prompt
- Basic conversation flow
- Product information

---

**Ready to upgrade? Follow the migration steps above!** 🚀

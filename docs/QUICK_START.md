# Quick Start Guide

Get your AI WhatsApp Backend up and running in 5 minutes!

---

## Step 1: Prerequisites Check ✅

Make sure you have:
- [ ] Python 3.11+ installed
- [ ] PostgreSQL running
- [ ] Redis running
- [ ] WhatsApp Business API credentials
- [ ] Google Gemini API key

---

## Step 2: Environment Setup (2 minutes)

### 1. Create `.env` file
```bash
cd C:\Users\KANCHAN\ai-backend
```

Create `.env` with these variables:
```env
# Database
DB_URL=postgresql://user:password@localhost:5432/dbname

# Redis
REDIS_URI=redis://localhost:6379

# Google AI
GOOGLE_API_KEY=your_gemini_api_key_here

# WhatsApp
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
VERIFY_TOKEN=your_verify_token_here

# Server
PORT=5000
ENVIRONMENT=development
```

### 2. Install Dependencies
```bash
.\_venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Setup Database
```bash
psql -U postgres -f db.sql
```

---

## Step 3: Start the System (1 minute)

### Terminal 1: Start Server
```bash
cd C:\Users\KANCHAN\ai-backend
.\_venv\Scripts\Activate.ps1
python run_server.py
```

You should see:
```
✅ Database connection verified
✅ Redis connection verified
✅ All systems operational
```

### Terminal 2: Start Celery
```bash
cd C:\Users\KANCHAN\ai-backend
.\_venv\Scripts\Activate.ps1
celery -A tasks worker -l info -P solo -Q default,state
```

You should see:
```
celery@shiva ready.
```

---

## Step 4: Verify Everything Works (1 minute)

```bash
.\check_celery.ps1
```

Expected output:
```
Server: healthy
Database: connected
Redis: connected
Celery: 1 workers active ✅
```

---

## Step 5: Run Your First Test (1 minute)

```bash
.\test_full_flow.ps1
```

Expected output:
```
✅ Webhook accepted message
✅ Takeover: takeover_complete
✅ Message sent: success
✅ Handback: handback_complete
```

---

## 🎉 You're Done!

Your AI WhatsApp Backend is now running!

### What's Running:
- ✅ FastAPI server on `http://localhost:5000`
- ✅ Celery worker processing background tasks
- ✅ Database storing conversations
- ✅ Redis caching and queuing messages
- ✅ AI ready to respond to customers

---

## Next Steps

### Test Operator Features
```bash
# Takeover a conversation
curl -X POST http://localhost:5000/api/v1/takeover -H "Content-Type: application/json" -d '{"phone":"919876543210"}'

# Send operator message
curl -X POST http://localhost:5000/api/v1/operator-message -H "Content-Type: application/json" -d '{"phone":"919876543210","message":"Hello!","messageId":null,"media":null}'

# Handback to AI
curl -X POST http://localhost:5000/api/v1/handback -H "Content-Type: application/json" -d '{"phone":"919876543210"}'
```

### View API Documentation
Open in browser: `http://localhost:5000/docs`

### Monitor System Health
```bash
# Check health
curl http://localhost:5000/health

# Check stats
curl http://localhost:5000/stats
```

---

## Common Issues

### Issue: "Database connection failed"
**Solution**: Check PostgreSQL is running and `DB_URL` in `.env` is correct

### Issue: "Redis connection failed"
**Solution**: Start Redis server: `redis-server`

### Issue: "Celery: no workers detected"
**Solution**: Start Celery worker (see Terminal 2 above)

### Issue: "WhatsApp API 401 error"
**Solution**: Check `WHATSAPP_ACCESS_TOKEN` in `.env` is valid

---

## Stopping the System

1. **Stop Celery**: Press `Ctrl+C` in Terminal 2
2. **Stop Server**: Press `Ctrl+C` in Terminal 1

---

## Need Help?

- **Full Documentation**: See `DOCUMENTATION.md`
- **Testing Guide**: See `TESTING_GUIDE.md`
- **Celery Setup**: See `celery_production.md`
- **Check Logs**: Look at terminal output for errors

---

## Daily Usage

### Starting the System
```bash
# Terminal 1
python run_server.py

# Terminal 2
celery -A tasks worker -l info -P solo -Q default,state
```

### Checking Status
```bash
.\check_celery.ps1
```

### Running Tests
```bash
.\test_full_flow.ps1
```

---

## Production Deployment

When ready for production:
1. See `DOCUMENTATION.md` → Production Deployment section
2. See `celery_production.md` for Celery service setup
3. Configure HTTPS/SSL
4. Set up monitoring and alerts
5. Enable database backups

---

**Congratulations! You're ready to build amazing AI-powered customer experiences!** 🚀

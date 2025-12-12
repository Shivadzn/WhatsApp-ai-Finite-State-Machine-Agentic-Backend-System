# AI WhatsApp Backend

AI-powered customer service backend for WhatsApp Business with seamless human operator handoff.

---

## 🚀 Quick Start

Get up and running in 5 minutes! See **[docs/QUICK_START.md](docs/QUICK_START.md)**

```bash
# 1. Setup environment
.\_venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configure .env file
# (See docs/QUICK_START.md for details)

# 3. Start server
python run_server.py

# 4. Start Celery (in new terminal)
celery -A tasks worker -l info -P solo -Q default,state,messages,status

# 5. Run comprehensive tests
.\run_all_tests.ps1
```

---

## 📚 Complete Documentation

| Document | Description |
|----------|-------------|
| **[docs/QUICK_START.md](docs/QUICK_START.md)** | Get running in 5 minutes |
| **[CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md)** | **New contributors start here!** |
| **[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)** | Complete system documentation |
| **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** | Full API documentation |
| **[docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)** | Testing procedures & scripts |
| **[TESTING_COMPLETE_GUIDE.md](TESTING_COMPLETE_GUIDE.md)** | **Comprehensive testing guide** |
| **[SSL_DOCS/SSL_SETUP_GUIDE.md](SSL_DOCS/SSL_SETUP_GUIDE.md)** | SSL/TLS setup for production |
| **[SSL_DOCS/SSL_QUICK_REFERENCE.md](SSL_DOCS/SSL_QUICK_REFERENCE.md)** | SSL quick reference card |
| **[test_celery/celery_production.md](test_celery/celery_production.md)** | Celery deployment guide |

---

## ✨ Features

- 🤖 **AI-Powered Conversations** - Google Gemini integration via LangGraph
- 👤 **Human Operator Handoff** - Seamless takeover and handback
- 📨 **Message Buffering** - Combines rapid-fire messages
- 🔄 **Async Processing** - Celery background tasks
- 💾 **Persistent State** - PostgreSQL + Redis
- 📱 **WhatsApp Integration** - Business API support
- 🧪 **Fully Tested** - Complete test suite included

---

## 🏗️ Architecture

```
WhatsApp ↔ FastAPI ↔ Celery ↔ LangGraph + Gemini
                ↓       ↓
           PostgreSQL  Redis
```

**Components:**
- **FastAPI** - HTTP API server
- **LangGraph** - AI conversation engine
- **Gemini** - Google's AI model
- **Celery** - Background task processing
- **PostgreSQL** - Persistent storage
- **Redis** - Cache & message queue

---

## 🔌 API Endpoints

### Operator Endpoints
```
POST /api/v1/takeover          # Operator takes over
POST /api/v1/operator-message  # Send operator message
POST /api/v1/handback          # Hand back to AI
```

### Webhook
```
GET  /webhook  # WhatsApp verification
POST /webhook  # Receive messages
```

### Monitoring
```
GET /health  # System health
GET /stats   # Statistics
GET /docs    # Interactive API docs
```

See **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** for complete details.

---

## 🧪 Testing

### Quick Tests

```bash
# Run comprehensive test suite (recommended)
.\run_all_tests.ps1
# Expected: 92-100% success rate

# Check system health
.\test_celery\check_celery.ps1

# Test full workflow
.\test_celery\test_full_flow.ps1

# Test edge cases
.\test_endpoints_scripts\test_edge_cases.ps1

# Test integration
.\test_endpoints_scripts\test_integration.ps1
```

**Latest Test Results:** 25/27 tests passing (92.59%) - See [TEST_RESULTS_ANALYSIS.md](TEST_RESULTS_ANALYSIS.md)

### What Gets Tested

- ✅ **System Health** - Database, Redis, Celery workers
- ✅ **Webhook Processing** - Message reception and buffering
- ✅ **AI Conversations** - LangGraph + Gemini responses
- ✅ **Operator Flow** - Takeover, messages, handback
- ✅ **Media Handling** - Send images, videos, audio
- ✅ **Edge Cases** - Error handling, validation
- ✅ **Load Testing** - Multiple conversations, rapid messages
- ✅ **State Management** - LangGraph state persistence

See **[TESTING_COMPLETE_GUIDE.md](TESTING_COMPLETE_GUIDE.md)** for detailed testing procedures.

---

## ⚙️ Configuration

Create `.env` file:

```env
# Database
DB_URL=postgresql://user:password@localhost:5432/dbname

# Redis
REDIS_URI=redis://localhost:6379

# Google AI
GOOGLE_API_KEY=your_gemini_api_key

# WhatsApp
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
VERIFY_TOKEN=your_verify_token

# Server
PORT=5000
ENVIRONMENT=development
```

---

## 📦 Requirements

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- WhatsApp Business API account
- Google Cloud account (Gemini API)

---

## 🚀 Production Deployment

See **[test_celery/celery_production.md](test_celery/celery_production.md)** for:
- Systemd service setup (Linux)
- NSSM service setup (Windows)
- Docker deployment
- Monitoring with Flower
- Performance tuning

See **[SSL_DOCS/SSL_SETUP_GUIDE.md](SSL_DOCS/SSL_SETUP_GUIDE.md)** for:
- SSL certificate setup
- HTTPS configuration
- Production security

---

## 📊 System Status

✅ **Production Ready**

- ✅ All operator endpoints working
- ✅ Edge cases handled
- ✅ Full customer flow tested
- ✅ Celery workers processing
- ✅ Database operations verified
- ✅ WhatsApp integration working

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI |
| **AI** | Google Gemini + LangGraph |
| **Database** | PostgreSQL |
| **Cache** | Redis |
| **Tasks** | Celery |
| **Messaging** | WhatsApp Business API |
| **ORM** | SQLAlchemy |

---

## 📖 Documentation Structure

```
├── README.md                      # This file - project overview
├── CONTRIBUTOR_GUIDE.md           # Contribution guidelines
├── TESTING_COMPLETE_GUIDE.md      # Comprehensive testing guide
├── run_all_tests.ps1              # Complete test suite runner
│
├── docs/
│   ├── QUICK_START.md             # 5-minute setup guide
│   ├── DOCUMENTATION.md           # Complete system docs
│   ├── API_REFERENCE.md           # API documentation
│   └── TESTING_GUIDE.md           # Testing procedures
│
├── SSL_DOCS/
│   ├── SSL_SETUP_GUIDE.md         # SSL setup for production
│   ├── SSL_QUICK_REFERENCE.md     # SSL quick reference
│   └── SSL_ARCHITECTURE.md        # SSL architecture details
│
├── test_celery/
│   ├── check_celery.ps1           # Health check script
│   ├── test_full_flow.ps1         # Full workflow test
│   └── celery_production.md       # Celery deployment guide
│
└── test_endpoints_scripts/
    ├── test_integration.ps1       # Integration tests
    ├── test_edge_cases.ps1        # Edge case tests
    └── test_simple.ps1            # Simple endpoint tests
```

---

## 🔍 Troubleshooting

### Celery not running?
```bash
celery -A tasks worker -l info -P solo -Q default,state,messages,status
```

### Database connection failed?
Check PostgreSQL is running and `DB_URL` in `.env`

### Redis connection failed?
```bash
redis-server
# Test: redis-cli ping (should return PONG)
```

### WhatsApp API errors?
Verify `WHATSAPP_ACCESS_TOKEN` in `.env`

### Tests failing?
1. Run health check: `.\test_celery\check_celery.ps1`
2. Check all services are running
3. Verify environment variables in `.env`
4. See **[TESTING_COMPLETE_GUIDE.md](TESTING_COMPLETE_GUIDE.md)** for detailed troubleshooting

See **[docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)** → Troubleshooting section

---

## 📝 License

See LICENSE file for details.

---

## 🙏 Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Google Gemini](https://ai.google.dev/)
- [Celery](https://docs.celeryq.dev/)
- [PostgreSQL](https://www.postgresql.org/)
- [Redis](https://redis.io/)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)

---

**🎉 Ready to build amazing AI-powered customer experiences!**

### Getting Started
1. **Setup:** Follow **[docs/QUICK_START.md](docs/QUICK_START.md)** → Get running in 5 minutes!
2. **Test:** Run `.\run_all_tests.ps1` → Verify everything works
3. **Deploy:** See **[test_celery/celery_production.md](test_celery/celery_production.md)** → Go to production

### Need Help?
- 📖 **Documentation:** [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)
- 🧪 **Testing Issues:** [TESTING_COMPLETE_GUIDE.md](TESTING_COMPLETE_GUIDE.md)
- 🤝 **Contributing:** [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md)
- 🔒 **SSL Setup:** [SSL_DOCS/SSL_SETUP_GUIDE.md](SSL_DOCS/SSL_SETUP_GUIDE.md)

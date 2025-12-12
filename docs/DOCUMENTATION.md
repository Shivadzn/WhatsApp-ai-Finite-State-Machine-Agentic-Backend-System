# AI WhatsApp Backend - Complete Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [Running the System](#running-the-system)
6. [API Endpoints](#api-endpoints)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)
9. [Production Deployment](#production-deployment)

---

## System Overview

### What This System Does
An AI-powered customer service backend for WhatsApp Business that:
- Handles customer conversations using Google's Gemini AI
- Supports seamless human operator handoff
- Buffers and deduplicates messages
- Maintains conversation state and history
- Processes messages asynchronously using Celery

### Technology Stack
- **Backend Framework**: FastAPI (Python)
- **AI Engine**: LangGraph + Google Gemini
- **Database**: PostgreSQL
- **Cache & Queue**: Redis
- **Task Queue**: Celery
- **Messaging**: WhatsApp Business API
- **ORM**: SQLAlchemy

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     WhatsApp Business API                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Webhook    │  │  Operator    │  │   Health     │      │
│  │  Endpoints   │  │  Endpoints   │  │   Checks     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │    Redis     │  │    Celery    │
│   Database   │  │ Cache/Queue  │  │   Workers    │
└──────────────┘  └──────────────┘  └──────┬───────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │  LangGraph   │
                                    │  + Gemini AI │
                                    └──────────────┘
```

### Data Flow

#### Incoming Customer Message
```
Customer → WhatsApp → Webhook → Message Buffer → Celery → AI → WhatsApp → Customer
```

#### Operator Message
```
Operator → API → WhatsApp → Customer
                 ↓
              Database → Celery → LangGraph (sync to AI memory)
```

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- WhatsApp Business API account
- Google Cloud account (for Gemini API)

### Step 1: Clone and Setup Virtual Environment
```bash
cd C:\Users\KANCHAN\ai-backend
python -m venv _venv
.\_venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Database Setup
```bash
# Connect to PostgreSQL
psql -U postgres

# Run the schema
\i db.sql
```

### Step 4: Environment Configuration
Create `.env` file with required variables (see Configuration section).

---

## Configuration

### Environment Variables (.env)

#### Required Variables
```env
# Database
DB_URL=postgresql://user:password@localhost:5432/dbname

# Redis
REDIS_URI=redis://localhost:6379

# Google AI
GOOGLE_API_KEY=your_gemini_api_key

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_whatsapp_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
VERIFY_TOKEN=your_webhook_verify_token

# Server
PORT=5000
ENVIRONMENT=development
```

#### Optional Variables
```env
# Logging
LOG_LEVEL=INFO

# Celery
CELERY_BROKER_URL=redis://localhost:6379
CELERY_RESULT_BACKEND=redis://localhost:6379
```

---

## Running the System

### Development Mode

#### Terminal 1: Start FastAPI Server
```bash
cd C:\Users\KANCHAN\ai-backend
.\_venv\Scripts\Activate.ps1
python run_server.py
```

#### Terminal 2: Start Celery Worker
```bash
cd C:\Users\KANCHAN\ai-backend
.\_venv\Scripts\Activate.ps1
celery -A tasks worker -l info -P solo -Q default,state
```

### Verify System is Running
```bash
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

## API Endpoints

### Webhook Endpoints

#### GET /webhook
**Purpose**: WhatsApp webhook verification

**Query Parameters**:
- `hub.mode`: "subscribe"
- `hub.verify_token`: Your verification token
- `hub.challenge`: Challenge string

**Response**: Returns challenge string if token is valid

#### POST /webhook
**Purpose**: Receive incoming WhatsApp messages and status updates

**Request Body**: WhatsApp webhook payload

**Response**: `{"status": "received"}`

### Operator Endpoints

#### POST /api/v1/takeover
**Purpose**: Operator takes over conversation from AI

**Request Body**:
```json
{
  "phone": "919876543210"
}
```

**Response**:
```json
{
  "status": "takeover_complete"
}
```

**What Happens**:
1. Sets `human_intervention_required = TRUE` in database
2. Queues Celery task to update LangGraph state
3. AI stops responding to customer messages

#### POST /api/v1/operator-message
**Purpose**: Send message as operator

**Request Body**:
```json
{
  "phone": "919876543210",
  "message": "Hello! How can I help you?",
  "messageId": null,
  "media": null
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Message queued for processing",
  "message_id": "wamid.HBgMOTE5ODc2NTQzMjEwFQIAERgS..."
}
```

**What Happens**:
1. Sends message via WhatsApp API
2. Stores message in database
3. Queues Celery task to sync message to AI conversation history

#### POST /api/v1/handback
**Purpose**: Hand conversation back to AI

**Request Body**:
```json
{
  "phone": "919876543210"
}
```

**Response**:
```json
{
  "status": "handback_complete"
}
```

**What Happens**:
1. Sets `human_intervention_required = FALSE` in database
2. Queues Celery task to update LangGraph state
3. AI resumes responding to customer messages

### Health & Monitoring

#### GET /health
**Purpose**: System health check

**Response**:
```json
{
  "status": "healthy",
  "checks": {
    "database": "connected",
    "redis": "connected",
    "celery": "1 workers active"
  }
}
```

#### GET /stats
**Purpose**: System statistics

**Response**:
```json
{
  "buffer": {
    "active_buffers": 0
  },
  "deduplication": {
    "cache_type": "redis"
  },
  "environment": "development"
}
```

---

## Testing

### Available Test Scripts

#### 1. Basic Health Check
```bash
.\check_celery.ps1
```
Verifies all system components are running.

#### 2. Full Customer Flow Test
```bash
.\test_full_flow.ps1
```
Tests complete workflow:
- Customer sends message
- Operator takeover
- Operator sends message
- Handback to AI

### Manual Testing with cURL

#### Test Takeover
```bash
curl -X POST http://localhost:5000/api/v1/takeover \
  -H "Content-Type: application/json" \
  -d '{"phone":"919876543210"}'
```

#### Test Operator Message
```bash
curl -X POST http://localhost:5000/api/v1/operator-message \
  -H "Content-Type: application/json" \
  -d '{"phone":"919876543210","message":"Test message","messageId":null,"media":null}'
```

---

## Troubleshooting

### Common Issues

#### 1. Celery Workers Not Running
**Symptom**: Health check shows "no workers detected"

**Solution**:
```bash
celery -A tasks worker -l info -P solo -Q default,state
```

#### 2. Database Connection Error
**Symptom**: `FATAL: password authentication failed`

**Solution**: Check `DB_URL` in `.env` file

#### 3. Redis Connection Error
**Symptom**: `Error 111 connecting to localhost:6379`

**Solution**: Start Redis server
```bash
redis-server
```

#### 4. WhatsApp API 400 Error
**Symptom**: "Failed to send message. Status: 400"

**Solution**: 
- Check `WHATSAPP_ACCESS_TOKEN` is valid
- Verify phone number format (include country code)
- Check WhatsApp API quota

#### 5. Tasks Not Processing
**Symptom**: Messages queued but not processed

**Solution**:
1. Check Celery is running
2. Check Redis is accessible
3. View Celery logs for errors

### Viewing Logs

#### Server Logs
Check terminal where `python run_server.py` is running

#### Celery Logs
Check terminal where Celery worker is running

#### Database Logs
```bash
# View recent messages
psql -U postgres -d dbname -c "SELECT * FROM message ORDER BY created_at DESC LIMIT 10;"
```

---

## Production Deployment

### System Requirements
- **CPU**: 2+ cores
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 20GB+ SSD
- **OS**: Linux (Ubuntu 20.04+ recommended) or Windows Server

### Deployment Checklist

#### 1. Environment Setup
- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Use strong database passwords
- [ ] Enable Redis authentication
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS certificates

#### 2. Database
- [ ] Enable PostgreSQL backups
- [ ] Set up connection pooling
- [ ] Configure proper indexes
- [ ] Enable query logging

#### 3. Application
- [ ] Use Gunicorn/Uvicorn with multiple workers
- [ ] Set up process manager (systemd/supervisor)
- [ ] Configure logging to files
- [ ] Set up log rotation

#### 4. Celery
- [ ] Run as system service
- [ ] Configure multiple workers
- [ ] Set up monitoring (Flower)
- [ ] Enable task result persistence

#### 5. Monitoring
- [ ] Set up health check monitoring
- [ ] Configure alerts for failures
- [ ] Monitor task queue length
- [ ] Track API response times

### Production Configuration

See `celery_production.md` for detailed Celery setup instructions.

---

## Database Schema

### Tables

#### conversation
```sql
- id: SERIAL PRIMARY KEY
- phone: VARCHAR(20) UNIQUE
- name: VARCHAR(100)
- human_intervention_required: BOOLEAN DEFAULT FALSE
- last_message_id: INTEGER
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

#### message
```sql
- id: SERIAL PRIMARY KEY
- conversation_id: INTEGER REFERENCES conversation(id)
- direction: ENUM('inbound', 'outbound')
- sender_type: ENUM('customer', 'ai', 'operator')
- sender_id: VARCHAR(100)
- external_id: VARCHAR(255)
- has_text: BOOLEAN
- message_text: TEXT
- media_info: JSONB
- provider_ts: TIMESTAMP
- extra_metadata: JSONB
- status: ENUM('sent', 'delivered', 'read', 'failed')
- created_at: TIMESTAMP
```

---

## Celery Tasks

### Task Types

#### 1. update_langgraph_state_task
**Queue**: `state`  
**Priority**: 8  
**Purpose**: Update AI conversation state (takeover/handback)  
**Execution Time**: 100-200ms

#### 2. sync_operator_message_to_graph_task
**Queue**: `state`  
**Priority**: 7  
**Purpose**: Sync operator messages to AI memory  
**Execution Time**: 150-800ms

#### 3. process_message_task
**Queue**: `default`  
**Priority**: 5  
**Purpose**: Process customer messages with AI  
**Execution Time**: 2-10 seconds

#### 4. check_buffer_task
**Queue**: `default`  
**Priority**: 3  
**Purpose**: Check if buffered messages should be processed  
**Execution Time**: 10-50ms

#### 5. update_message_status_task
**Queue**: `default`  
**Priority**: 1  
**Purpose**: Update message delivery status  
**Execution Time**: 50-100ms

---

## Security Best Practices

1. **API Keys**: Never commit `.env` to version control
2. **Database**: Use strong passwords, enable SSL connections
3. **Redis**: Enable authentication, bind to localhost only
4. **WhatsApp**: Validate webhook signatures
5. **HTTPS**: Use SSL/TLS in production
6. **Rate Limiting**: Implement API rate limits
7. **Input Validation**: All user inputs are validated via Pydantic

---

## Support & Maintenance

### Regular Maintenance Tasks

#### Daily
- Monitor Celery task queue length
- Check error logs
- Verify health endpoint

#### Weekly
- Review database size and performance
- Clear old Redis keys
- Check disk space

#### Monthly
- Update dependencies
- Review and optimize database queries
- Backup database
- Review AI conversation quality

### Getting Help

For issues or questions:
1. Check this documentation
2. Review logs (server + Celery)
3. Check `celery_production.md` for Celery-specific issues
4. Verify all environment variables are set correctly

---

## Changelog

### Version 1.0.0 (Current)
- Initial release
- AI-powered conversations with Gemini
- Operator handoff functionality
- Message buffering and deduplication
- Celery background processing
- WhatsApp Business API integration
- Complete testing suite

---

## License

See LICENSE file for details.

---

## Credits

Built with:
- FastAPI
- LangGraph
- Google Gemini
- Celery
- PostgreSQL
- Redis
- WhatsApp Business API

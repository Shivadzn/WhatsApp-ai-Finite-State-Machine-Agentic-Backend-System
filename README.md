#  WhatsApp AI Backend

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![Celery](https://img.shields.io/badge/Celery-5.3+-37814A.svg)](https://docs.celeryq.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-FF6F00.svg)](https://langchain-ai.github.io/langgraph/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Production-ready customer service backend for WhatsApp Business with AI-powered conversations and human operator handoff capabilities.

---

## Overview

This system provides an automated customer service solution integrating WhatsApp Business API with Google Gemini AI, featuring seamless human operator intervention when needed. Built with FastAPI, LangGraph, and Celery for scalable asynchronous processing.

### Key Features

- AI-powered conversation management using Google Gemini via LangGraph
- Human operator takeover and handback functionality
- Message buffering for handling rapid user inputs
- Asynchronous task processing with Celery
- Persistent state management using PostgreSQL and Redis
- WhatsApp Business API integration
- Comprehensive test coverage
- Multilingual support

---

## Architecture

### System Overview

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#1e293b','primaryTextColor':'#f1f5f9','primaryBorderColor':'#475569','lineColor':'#64748b','secondaryColor':'#334155','tertiaryColor':'#0f172a'}}}%%

flowchart TB
    subgraph external["External Services"]
        direction LR
        user["WhatsApp User"]
        whatsapp["WhatsApp Business API"]
    end

    subgraph api["FastAPI Server"]
        direction TB
        webhook["/webhook<br/><small>Message Reception</small>"]
        health["/health<br/><small>System Status</small>"]
        
        subgraph operator_api["Operator Endpoints"]
            takeover["/api/v1/takeover<br/><small>Assume Control</small>"]
            opmsg["/api/v1/operator-message<br/><small>Send Message</small>"]
            handback["/api/v1/handback<br/><small>Return to AI</small>"]
        end
    end

    subgraph celery["Asynchronous Processing Layer"]
        direction TB
        buffer["Message Buffer<br/><small>15-second aggregation window</small>"]
        
        subgraph queues["Celery Queues"]
            direction LR
            q_msg["messages"]
            q_state["state"]
            q_status["status"]
        end
        
        processor["Message Processor<br/><small>Background Task</small>"]
    end

    subgraph langgraph["LangGraph State Machine"]
        direction TB
        
        decision{"Operator<br/>Control Active?"}
        
        subgraph ai_flow["AI Processing"]
            agent["AI Agent<br/><small>Google Gemini</small>"]
            tools["Tool Executor"]
            tool_media["RespondWithMedia<br/><small>Send Samples</small>"]
            tool_escalate["RequestIntervention<br/><small>Human Handoff</small>"]
        end
        
        state_mgmt["State Manager<br/><small>Conversation Context</small>"]
    end

    subgraph data["Persistence Layer"]
        direction LR
        postgres[("PostgreSQL<br/><small>Conversation History</small>")]
        redis[("Redis<br/><small>Session Cache</small>")]
    end

    subgraph operator["Human Operator Interface"]
        direction TB
        op_human["Operator"]
        op_dash["Dashboard<br/><small>Monitoring & Control</small>"]
    end

    subgraph output["Response Handler"]
        direction TB
        sender["WhatsApp Sender<br/><small>Message Delivery</small>"]
        logger["Response Logger<br/><small>Audit Trail</small>"]
    end

    user -->|"1. Send Message"| whatsapp
    whatsapp -->|"2. Webhook POST"| webhook
    webhook -->|"3. Queue"| buffer
    buffer -->|"4. Aggregate"| q_msg
    q_msg -->|"5. Process"| processor
    
    processor -->|"6. Load Context"| redis
    processor -->|"7. Route"| decision
    
    decision -->|"AI Mode"| agent
    agent -->|"8a. Generate"| state_mgmt
    agent -->|"8b. Execute"| tools
    tools --> tool_media
    tools --> tool_escalate
    tool_media -->|"Media Response"| sender
    tool_escalate -->|"Alert"| op_dash
    
    decision -->|"Operator Mode"| state_mgmt
    state_mgmt -->|"Silent"| logger
    
    state_mgmt -->|"Persist"| postgres
    state_mgmt -->|"Cache"| redis
    state_mgmt -->|"Response"| sender
    
    op_human -->|"Monitor"| op_dash
    op_dash -->|"Takeover"| takeover
    takeover -->|"Enable Control"| state_mgmt
    op_human -->|"Message"| opmsg
    opmsg -->|"Send as Operator"| sender
    op_human -->|"Release"| handback
    handback -->|"Return to AI"| state_mgmt
    
    sender -->|"9. Deliver"| whatsapp
    whatsapp -->|"10. Receive"| user
    sender -->|"Log"| logger
    logger -->|"Store"| postgres
    
    health -.->|"Check"| postgres
    health -.->|"Check"| redis
    health -.->|"Check"| q_msg

    classDef externalStyle fill:#10b981,stroke:#059669,stroke-width:2px,color:#fff,font-weight:bold
    classDef apiStyle fill:#3b82f6,stroke:#2563eb,stroke-width:2px,color:#fff
    classDef celeryStyle fill:#f59e0b,stroke:#d97706,stroke-width:2px,color:#fff
    classDef aiStyle fill:#8b5cf6,stroke:#7c3aed,stroke-width:2px,color:#fff
    classDef dataStyle fill:#ef4444,stroke:#dc2626,stroke-width:2px,color:#fff
    classDef operatorStyle fill:#06b6d4,stroke:#0891b2,stroke-width:2px,color:#fff
    classDef outputStyle fill:#14b8a6,stroke:#0d9488,stroke-width:2px,color:#fff
    classDef decisionStyle fill:#f97316,stroke:#ea580c,stroke-width:3px,color:#fff

    class user,whatsapp externalStyle
    class webhook,health,takeover,opmsg,handback apiStyle
    class buffer,q_msg,q_state,q_status,processor celeryStyle
    class agent,tools,tool_media,tool_escalate,state_mgmt aiStyle
    class postgres,redis dataStyle
    class op_human,op_dash operatorStyle
    class sender,logger outputStyle
    class decision decisionStyle
```

### Component Description

**Core Components:**
- **FastAPI**: HTTP API server
- **LangGraph**: Conversation flow management
- **Google Gemini**: AI language model
- **Celery**: Background task processing
- **PostgreSQL**: Data persistence
- **Redis**: Caching and message queuing

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- WhatsApp Business API account
- Google Cloud account with Gemini API access

### Installation

1. **Setup virtual environment:**
```bash
.\_venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. **Configure environment variables:**

Create a `.env` file with the following:

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

3. **Start the services:**

```bash
# Terminal 1: Start FastAPI server
python run_server.py

# Terminal 2: Start Celery worker
celery -A tasks worker -l info -P solo -Q default,state,messages,status
```

4. **Verify installation:**
```bash
.\run_all_tests.ps1
```

For detailed setup instructions, see [docs/QUICK_START.md](docs/QUICK_START.md)

---

## API Endpoints

### Operator Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/takeover` | POST | Operator assumes control of conversation |
| `/api/v1/operator-message` | POST | Send message as operator |
| `/api/v1/handback` | POST | Return conversation to AI |

### Webhook Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | GET | WhatsApp webhook verification |
| `/webhook` | POST | Receive WhatsApp messages |

### System Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/stats` | GET | System statistics |
| `/docs` | GET | Interactive API documentation |

Complete API documentation: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

---

## Testing

### Running Tests

```bash
# Complete test suite
.\run_all_tests.ps1

# Individual test categories
.\test_celery\check_celery.ps1           # System health
.\test_celery\test_full_flow.ps1         # End-to-end workflow
.\test_endpoints_scripts\test_edge_cases.ps1    # Edge cases
.\test_endpoints_scripts\test_integration.ps1   # Integration tests
```

### Test Coverage

The test suite validates:
- System health (database, Redis, Celery workers)
- Webhook processing and message buffering
- AI conversation flows
- Operator takeover/handback mechanisms
- Media handling (images, videos, audio)
- Error handling and edge cases
- State persistence and recovery
- Load handling and concurrency

Current test results: 25/27 passing (92.59%)

For detailed testing procedures, see [TESTING_COMPLETE_GUIDE.md](TESTING_COMPLETE_GUIDE.md)

---

## Production Deployment

### System Service Setup

**Linux (systemd):**
See [test_celery/celery_production.md](test_celery/celery_production.md)

**Windows (NSSM):**
See [test_celery/celery_production.md](test_celery/celery_production.md)

**Docker:**
Container configuration available in deployment documentation.

### SSL/TLS Configuration

For production HTTPS setup:
- [SSL_DOCS/SSL_SETUP_GUIDE.md](SSL_DOCS/SSL_SETUP_GUIDE.md)
- [SSL_DOCS/SSL_QUICK_REFERENCE.md](SSL_DOCS/SSL_QUICK_REFERENCE.md)

### Monitoring

Celery task monitoring with Flower:
```bash
celery -A tasks flower --port=5555
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [QUICK_START.md](docs/QUICK_START.md) | Initial setup guide |
| [DOCUMENTATION.md](docs/DOCUMENTATION.md) | Complete system documentation |
| [API_REFERENCE.md](docs/API_REFERENCE.md) | API endpoint reference |
| [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | Testing procedures |
| [TESTING_COMPLETE_GUIDE.md](TESTING_COMPLETE_GUIDE.md) | Comprehensive testing guide |
| [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md) | Contribution guidelines |
| [SSL_SETUP_GUIDE.md](SSL_DOCS/SSL_SETUP_GUIDE.md) | SSL/TLS configuration |
| [celery_production.md](test_celery/celery_production.md) | Celery deployment guide |

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| API Framework | FastAPI |
| AI Integration | Google Gemini, LangGraph |
| Database | PostgreSQL |
| Cache | Redis |
| Task Queue | Celery |
| Messaging | WhatsApp Business API |
| ORM | SQLAlchemy |

---

## Troubleshooting

### Common Issues

**Celery worker not running:**
```bash
celery -A tasks worker -l info -P solo -Q default,state,messages,status
```

**Database connection failed:**
- Verify PostgreSQL is running
- Check `DB_URL` in `.env` file

**Redis connection failed:**
```bash
# Start Redis server
redis-server

# Test connection
redis-cli ping
```

**WhatsApp API errors:**
- Verify `WHATSAPP_ACCESS_TOKEN` is valid
- Check phone number ID configuration

**Test failures:**
1. Run health check: `.\test_celery\check_celery.ps1`
2. Verify all services are running
3. Confirm environment variables are set correctly
4. Consult [TESTING_COMPLETE_GUIDE.md](TESTING_COMPLETE_GUIDE.md)

For detailed troubleshooting, see [docs/DOCUMENTATION.md](docs/DOCUMENTATION.md)

---

## Project Status

**Current State:** Production ready

- Operator endpoints operational
- Edge case handling implemented
- Full customer workflow tested
- Celery workers processing reliably
- Database operations verified
- WhatsApp integration functional

---

## Contributing

See [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md) for contribution guidelines.

---

## License

See LICENSE file for licensing details.

---

## Dependencies

This project utilizes:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Conversation management
- [Google Gemini](https://ai.google.dev/) - AI model
- [Celery](https://docs.celeryq.dev/) - Task queue
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Redis](https://redis.io/) - Cache and message broker
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp) - Messaging platform

---

## Support

For issues or questions:
1. Check relevant documentation in [docs/](docs/)
2. Review [TESTING_COMPLETE_GUIDE.md](TESTING_COMPLETE_GUIDE.md) for common problems
3. Consult [CONTRIBUTOR_GUIDE.md](CONTRIBUTOR_GUIDE.md) for development guidance

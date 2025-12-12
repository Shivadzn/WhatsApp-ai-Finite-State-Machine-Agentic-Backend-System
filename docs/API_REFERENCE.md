# API Reference

Complete API documentation for the AI WhatsApp Backend.

---

## Base URL
```
http://localhost:5000
```

---

## Authentication
Currently, the API does not require authentication for operator endpoints. In production, implement:
- API keys
- JWT tokens
- OAuth 2.0

---

## Endpoints

### 1. Webhook Endpoints

#### GET /webhook
**Purpose**: WhatsApp webhook verification

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| hub.mode | string | Yes | Must be "subscribe" |
| hub.verify_token | string | Yes | Your verification token |
| hub.challenge | string | Yes | Challenge string from WhatsApp |

**Response**: `200 OK`
```
<challenge_string>
```

**Response**: `403 Forbidden`
```json
{
  "detail": "Verification failed"
}
```

**Example**:
```bash
curl "http://localhost:5000/webhook?hub.mode=subscribe&hub.verify_token=your_token&hub.challenge=test123"
```

---

#### POST /webhook
**Purpose**: Receive incoming WhatsApp messages and status updates

**Request Body**: WhatsApp webhook payload (see WhatsApp API documentation)

**Response**: `200 OK`
```json
{
  "status": "received"
}
```

**What Happens**:
1. Message is deduplicated (prevents duplicate processing)
2. Message is buffered (2-second debounce)
3. Celery task queued to process buffer
4. AI generates response (if not in operator mode)

**Example**:
```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
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
  }'
```

---

### 2. Operator Endpoints

#### POST /api/v1/takeover
**Purpose**: Operator takes over conversation from AI

**Request Body**:
```json
{
  "phone": "string"  // Required: Customer phone number with country code
}
```

**Response**: `200 OK`
```json
{
  "status": "takeover_complete"
}
```

**Response**: `400 Bad Request`
```json
{
  "detail": "Phone number is required"
}
```

**Response**: `404 Not Found`
```json
{
  "detail": "No conversation found for phone number 919876543210"
}
```

**Response**: `500 Internal Server Error`
```json
{
  "detail": "Takeover failed: <error_message>"
}
```

**Side Effects**:
1. Sets `human_intervention_required = TRUE` in database
2. Queues Celery task: `update_langgraph_state_task`
3. Updates LangGraph state: `{"operator_active": True}`
4. AI stops auto-responding to customer messages

**Example**:
```bash
curl -X POST http://localhost:5000/api/v1/takeover \
  -H "Content-Type: application/json" \
  -d '{"phone":"919876543210"}'
```

---

#### POST /api/v1/operator-message
**Purpose**: Send message to customer as operator

**Request Body**:
```json
{
  "phone": "string",        // Required: Customer phone number
  "message": "string",      // Required: Message text (if no media)
  "messageId": "string",    // Optional: Message ID
  "media": {                // Optional: Media information
    "id": "string",
    "mimeType": "string"
  }
}
```

**Response**: `200 OK`
```json
{
  "status": "success",
  "message": "Message queued for processing",
  "message_id": "wamid.HBgMOTE5ODc2NTQzMjEwFQIAERgS..."
}
```

**Response**: `400 Bad Request`
```json
{
  "detail": "Phone number is required"
}
// OR
{
  "detail": "Message text or media is required"
}
```

**Response**: `500 Internal Server Error`
```json
{
  "detail": "Failed to process message"
}
// OR
{
  "detail": "Failed to process media"
}
```

**Side Effects**:
1. Sends message via WhatsApp Business API
2. Stores message in database (direction: outbound, sender_type: operator)
3. Queues Celery task: `sync_operator_message_to_graph_task`
4. Syncs message to AI conversation history
5. Creates conversation if it doesn't exist

**Example**:
```bash
curl -X POST http://localhost:5000/api/v1/operator-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "919876543210",
    "message": "Hello! How can I help you?",
    "messageId": null,
    "media": null
  }'
```

---

#### POST /api/v1/handback
**Purpose**: Hand conversation back to AI

**Request Body**:
```json
{
  "phone": "string"  // Required: Customer phone number
}
```

**Response**: `200 OK`
```json
{
  "status": "handback_complete"
}
```

**Response**: `400 Bad Request`
```json
{
  "detail": "Phone number is required"
}
```

**Response**: `404 Not Found`
```json
{
  "detail": "No conversation found for phone number 919876543210"
}
```

**Response**: `500 Internal Server Error`
```json
{
  "detail": "Handback failed: <error_message>"
}
```

**Side Effects**:
1. Sets `human_intervention_required = FALSE` in database
2. Queues Celery task: `update_langgraph_state_task`
3. Updates LangGraph state: `{"operator_active": False}`
4. AI resumes auto-responding to customer messages

**Example**:
```bash
curl -X POST http://localhost:5000/api/v1/handback \
  -H "Content-Type: application/json" \
  -d '{"phone":"919876543210"}'
```

---

### 3. Health & Monitoring Endpoints

#### GET /health
**Purpose**: System health check

**Response**: `200 OK`
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

**Response**: `503 Service Unavailable`
```json
{
  "status": "unhealthy",
  "checks": {
    "database": "disconnected",
    "redis": "connected",
    "celery": "no workers detected"
  }
}
```

**Example**:
```bash
curl http://localhost:5000/health
```

---

#### GET /stats
**Purpose**: System statistics

**Response**: `200 OK`
```json
{
  "buffer": {
    "active_buffers": 0,
    "total_buffered": 0
  },
  "deduplication": {
    "cache_type": "redis",
    "total_deduplicated": 0
  },
  "environment": "development"
}
```

**Example**:
```bash
curl http://localhost:5000/stats
```

---

#### GET /
**Purpose**: Root endpoint

**Response**: `200 OK`
```json
{
  "message": "WhatsApp AI Backend is running",
  "version": "1.0.0",
  "docs": "/docs"
}
```

**Example**:
```bash
curl http://localhost:5000/
```

---

## Error Responses

### Standard Error Format
```json
{
  "detail": "Error message here"
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid input (missing fields, validation errors) |
| 404 | Not Found | Resource not found (conversation doesn't exist) |
| 422 | Unprocessable Entity | Pydantic validation failed |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | System unhealthy |

---

## Rate Limiting

Currently not implemented. For production, consider:
- 100 requests/minute per IP
- 1000 requests/hour per API key
- Burst allowance: 20 requests/second

---

## Request/Response Examples

### Complete Operator Workflow

#### 1. Takeover
```bash
curl -X POST http://localhost:5000/api/v1/takeover \
  -H "Content-Type: application/json" \
  -d '{"phone":"919876543210"}'
```

Response:
```json
{"status": "takeover_complete"}
```

#### 2. Send Message
```bash
curl -X POST http://localhost:5000/api/v1/operator-message \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "919876543210",
    "message": "Hello! I can help you with your order.",
    "messageId": null,
    "media": null
  }'
```

Response:
```json
{
  "status": "success",
  "message": "Message queued for processing",
  "message_id": "wamid.HBgMOTE5ODc2NTQzMjEwFQIAERgS..."
}
```

#### 3. Handback
```bash
curl -X POST http://localhost:5000/api/v1/handback \
  -H "Content-Type: application/json" \
  -d '{"phone":"919876543210"}'
```

Response:
```json
{"status": "handback_complete"}
```

---

## WebSocket Support

Not currently implemented. Future consideration for:
- Real-time operator notifications
- Live conversation updates
- Typing indicators

---

## API Versioning

Current version: `v1`

All operator endpoints are prefixed with `/api/v1/`

Future versions will use `/api/v2/`, `/api/v3/`, etc.

---

## CORS Configuration

Currently allows all origins in development.

For production, configure allowed origins in `app.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Interactive API Documentation

### Swagger UI
Visit: `http://localhost:5000/docs`

Features:
- Try out endpoints directly
- View request/response schemas
- See all available endpoints

### ReDoc
Visit: `http://localhost:5000/redoc`

Features:
- Clean, readable documentation
- Downloadable OpenAPI spec
- Code samples

---

## SDK / Client Libraries

Currently not available. Consider creating:
- Python client library
- JavaScript/TypeScript client
- React hooks for frontend integration

---

## Webhooks (Outgoing)

Not currently implemented. Future consideration for:
- Notify external systems of events
- Send conversation transcripts
- Alert on AI intervention requests

---

## Best Practices

### Phone Number Format
Always include country code:
- ✅ Good: `"919876543210"`
- ❌ Bad: `"9876543210"`

### Error Handling
Always check response status:
```javascript
const response = await fetch('/api/v1/takeover', {
  method: 'POST',
  body: JSON.stringify({phone: '919876543210'})
});

if (!response.ok) {
  const error = await response.json();
  console.error('Takeover failed:', error.detail);
}
```

### Retry Logic
Implement exponential backoff for failed requests:
```javascript
async function retryRequest(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await sleep(Math.pow(2, i) * 1000);
    }
  }
}
```

---

## Security Considerations

### Production Checklist
- [ ] Implement API key authentication
- [ ] Enable HTTPS/TLS
- [ ] Validate WhatsApp webhook signatures
- [ ] Implement rate limiting
- [ ] Add request logging
- [ ] Sanitize all inputs
- [ ] Use environment variables for secrets
- [ ] Enable CORS only for trusted domains

---

## Support

For API issues:
1. Check response error messages
2. Review server logs
3. Verify request format matches examples
4. Check system health: `GET /health`
5. Refer to `DOCUMENTATION.md`

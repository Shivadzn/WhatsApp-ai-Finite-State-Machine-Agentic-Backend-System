# Celery Production Setup Guide

## Overview
Celery handles all background tasks for the AI backend, including:
- AI message processing
- LangGraph state synchronization
- Message buffering and deduplication
- WhatsApp status updates

## Development Setup (Current)

### Start Celery Worker
```bash
celery -A tasks worker -l info -P solo -Q default,state
```

**Queues:**
- `default`: General tasks (message processing, status updates)
- `state`: High-priority state updates (takeover, handback, graph sync)

## Production Setup

### Linux (systemd service)

1. **Create service file:** `/etc/systemd/system/celery-worker.service`
```ini
[Unit]
Description=Celery Worker for AI Backend
After=network.target redis.service postgresql.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/ai-backend
Environment="PATH=/var/www/ai-backend/venv/bin"
ExecStart=/var/www/ai-backend/venv/bin/celery -A tasks worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=default,state \
    --max-tasks-per-child=100 \
    --time-limit=300 \
    --soft-time-limit=240

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-worker
sudo systemctl start celery-worker
sudo systemctl status celery-worker
```

### Windows (NSSM - Non-Sucking Service Manager)

1. **Download NSSM:** https://nssm.cc/download

2. **Install service:**
```powershell
nssm install CeleryWorker "C:\path\to\ai-backend\_venv\Scripts\celery.exe"
nssm set CeleryWorker AppParameters "-A tasks worker -l info -P solo -Q default,state"
nssm set CeleryWorker AppDirectory "C:\path\to\ai-backend"
nssm set CeleryWorker DisplayName "AI Backend Celery Worker"
nssm set CeleryWorker Description "Background task processor for WhatsApp AI"
nssm set CeleryWorker Start SERVICE_AUTO_START
nssm start CeleryWorker
```

### Docker

```dockerfile
# Celery worker service
celery-worker:
  build: .
  command: celery -A tasks worker -l info --concurrency=4 -Q default,state
  volumes:
    - .:/app
  environment:
    - REDIS_URI=${REDIS_URI}
    - DB_URL=${DB_URL}
    - GOOGLE_API_KEY=${GOOGLE_API_KEY}
  depends_on:
    - redis
    - postgres
  restart: unless-stopped
```

## Monitoring

### Flower (Web-based monitoring)

1. **Install:**
```bash
pip install flower
```

2. **Start:**
```bash
celery -A tasks flower --port=5555
```

3. **Access:** http://localhost:5555

### Health Checks

Monitor via API:
```bash
curl http://localhost:5000/health
```

Check for: `"celery": "1 worker(s) active"`

## Performance Tuning

### Worker Concurrency
```bash
# CPU-bound tasks (AI processing)
celery -A tasks worker --concurrency=4

# I/O-bound tasks (API calls)
celery -A tasks worker --concurrency=10
```

### Queue Priorities
- `state` queue: Priority 8-10 (takeover, handback, state updates)
- `default` queue: Priority 1-5 (message processing, status updates)

### Task Time Limits
- Hard limit: 300 seconds (5 minutes)
- Soft limit: 240 seconds (4 minutes)
- Max retries: 3 attempts
- Retry delay: 5 seconds (exponential backoff)

## Troubleshooting

### Workers not processing tasks
```bash
# Check Redis connection
redis-cli ping

# Check queue length
redis-cli LLEN celery
redis-cli LLEN state

# Restart workers
sudo systemctl restart celery-worker
```

### High memory usage
```bash
# Reduce max tasks per child
celery -A tasks worker --max-tasks-per-child=50
```

### Slow task processing
```bash
# Increase concurrency
celery -A tasks worker --concurrency=8

# Or add more workers
celery -A tasks worker -n worker1@%h &
celery -A tasks worker -n worker2@%h &
```

## Logs

### View logs
```bash
# systemd
sudo journalctl -u celery-worker -f

# Docker
docker logs -f celery-worker

# Windows (NSSM)
# Check: C:\path\to\ai-backend\logs\celery.log
```

### Log levels
- `DEBUG`: Detailed task execution
- `INFO`: Task start/completion (recommended)
- `WARNING`: Issues that don't stop execution
- `ERROR`: Failed tasks

## Best Practices

1. **Always run Celery in production** - Critical for AI functionality
2. **Monitor task queue length** - Alert if > 1000 tasks
3. **Set up alerts** - For worker failures or high error rates
4. **Use separate workers** - For different task types if needed
5. **Regular restarts** - Weekly to prevent memory leaks
6. **Backup Redis** - Contains queued tasks

## Security

1. **Secure Redis** - Use password authentication
2. **Network isolation** - Celery workers should only access Redis/DB
3. **Resource limits** - Prevent worker from consuming all CPU/memory
4. **Task validation** - Validate all task inputs

## Scaling

### Horizontal Scaling
```bash
# Multiple workers on same machine
celery -A tasks worker -n worker1@%h --concurrency=4 &
celery -A tasks worker -n worker2@%h --concurrency=4 &

# Multiple machines
# Just run celery workers on different servers pointing to same Redis
```

### Vertical Scaling
```bash
# Increase concurrency
celery -A tasks worker --concurrency=16
```

## Task Routing

Current routing (see `tasks.py`):
- `update_langgraph_state_task` → `state` queue (priority 8)
- `sync_operator_message_to_graph_task` → `state` queue (priority 7)
- `process_message_task` → `default` queue (priority 5)
- `check_buffer_task` → `default` queue (priority 3)
- `update_message_status_task` → `default` queue (priority 1)

## References

- Celery Docs: https://docs.celeryq.dev/
- Flower Docs: https://flower.readthedocs.io/
- Redis Docs: https://redis.io/docs/

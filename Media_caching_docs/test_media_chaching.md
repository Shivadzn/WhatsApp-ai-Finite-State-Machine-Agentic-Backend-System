# Media Caching Testing Guide

## Quick Test Checklist

### 1. Start the Application

```bash
# Activate virtual environment
_venv\Scripts\activate

# Start the server (in Terminal 1)
python run_server.py

# Start Celery worker (in Terminal 2)
celery -A tasks worker -l info -P solo -Q default,state,maintenance
```

### 2. Basic API Tests

#### Test Statistics Endpoint
```bash
curl http://localhost:5000/media/stats
```

**Expected Response:**
```json
{
  "status": "success",
  "statistics": {
    "total_requests": 0,
    "cache_hits": 0,
    "api_calls": 0,
    "failed_calls": 0,
    "expired_media": 0,
    "cache_hit_rate": "0%"
  }
}
```

#### Test Cleanup Endpoint
```bash
curl -X POST http://localhost:5000/media/cleanup
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Old media cleanup completed"
}
```

### 3. Media Download Tests

#### Test with Known Working Media ID
```bash
curl "http://localhost:5000/media?id=1167844115226607"
```

#### Test with Known Failed Media ID
```bash
curl "http://localhost:5000/media?id=2060674271006192"
```

#### Test with Timestamp (Simulating fresh media)
```bash
curl "http://localhost:5000/media?id=1167844115226607&timestamp=$(date +%s)"
```

#### Test with Old Timestamp (Simulating expired media)
```bash
# Get timestamp from 2 days ago
old_timestamp=$(($(date +%s) - 172800))
curl "http://localhost:5000/media?id=1167844115226607&timestamp=$old_timestamp"
```

### 4. Cache Behavior Tests

#### Test Failed Media Caching
```bash
# First request - should fail and cache the failure
curl "http://localhost:5000/media?id=2060674271006192"

# Second request - should skip API call (check logs)
curl "http://localhost:5000/media?id=2060674271006192"
```

#### Test Local Cache Creation
```bash
# Check if cache directory exists
ls -la tmp/whatsapp_media/

# If not, create it
mkdir -p tmp/whatsapp_media
chmod 755 tmp/whatsapp_media/
```

### 5. Redis Tests

#### Check Redis Connection
```bash
redis-cli ping
```

#### Check Failed Media Cache
```bash
redis-cli KEYS "failed_media:*"
```

#### Check Statistics
```bash
redis-cli HGETALL "media:stats"
```

#### Clear Failed Cache (if needed)
```bash
redis-cli DEL $(redis-cli KEYS "failed_media:*")
```

### 6. Log Monitoring

#### Monitor Application Logs
```bash
# In a new terminal, watch for cache-related logs
tail -f logs/app.log | grep -E "cache|expired|retry|failed_media|📊"
```

#### Monitor Celery Logs
```bash
# Watch Celery worker logs
tail -f celery.log | grep -E "cleanup|media"
```

### 7. End-to-End WhatsApp Test

#### Send a Fresh Media Message
1. Send a new image/video to your WhatsApp number
2. Check logs for successful download
3. Verify file appears in `tmp/whatsapp_media/`
4. Send the same media again
5. Check logs for "from local cache"

#### Reply to Old Message (24+ hours old)
1. Find an old message with media in your conversation
2. Reply to it
3. Check logs for "Media expired" warning
4. Verify no API call was made

### 8. Performance Tests

#### Load Test with Same Media ID
```bash
# Test 10 requests to same media
for i in {1..10}; do
  curl "http://localhost:5000/media?id=1167844115226607" &
done
wait

# Check statistics
curl http://localhost:5000/media/stats
```

#### Load Test with Failed Media ID
```bash
# Test 10 requests to failed media
for i in {1..10}; do
  curl "http://localhost:5000/media?id=2060674271006192" &
done
wait

# Check statistics
curl http://localhost:5000/media/stats
```

### 9. Cleanup Task Test

#### Manual Cleanup
```bash
# Trigger manual cleanup
curl -X POST http://localhost:5000/media/cleanup

# Check logs for cleanup results
tail -f logs/app.log | grep "cleanup"
```

#### Scheduled Cleanup (Optional)
```bash
# Test the Celery task directly
celery -A tasks call tasks.cleanup_old_media
```

### 10. Error Handling Tests

#### Test with Invalid Media ID
```bash
curl "http://localhost:5000/media?id=invalid_id"
```

#### Test with Missing Parameters
```bash
curl "http://localhost:5000/media"
```

#### Test Redis Failure (Optional)
```bash
# Stop Redis temporarily
redis-cli shutdown

# Test media download - should still work
curl "http://localhost:5000/media?id=1167844115226607"

# Restart Redis
redis-server
```

## Expected Results

### ✅ Success Indicators

1. **Statistics Endpoint Returns Data**
   - `total_requests` > 0 after making requests
   - `cache_hit_rate` increases with repeated requests

2. **Failed Media Caching**
   - First request to failed ID: API call + error
   - Second request: No API call (check logs)

3. **Local Cache Creation**
   - Files appear in `tmp/whatsapp_media/`
   - Subsequent requests show "from local cache"

4. **Expiration Handling**
   - Old timestamps show "Media expired" in logs
   - No API calls for expired media

5. **Retry Logic**
   - Network timeouts show retry attempts
   - Exponential backoff (2s, 4s delays)

### ⚠️ Warning Signs

1. **No Cache Directory**
   - `tmp/whatsapp_media/` doesn't exist
   - Fix: `mkdir -p tmp/whatsapp_media`

2. **Redis Connection Issues**
   - `redis-cli ping` fails
   - Fix: Check Redis configuration

3. **No Statistics**
   - `/media/stats` returns empty or error
   - Fix: Check Redis connectivity

4. **No Cache Hits**
   - `cache_hit_rate` stays at 0%
   - Fix: Check file permissions, Redis connection

## Troubleshooting Commands

### Check System Status
```bash
# Check Redis
redis-cli ping
redis-cli info memory

# Check cache directory
ls -la tmp/whatsapp_media/
du -sh tmp/whatsapp_media/

# Check application
curl http://localhost:5000/health
curl http://localhost:5000/media/stats
```

### Reset Cache (if needed)
```bash
# Clear Redis cache
redis-cli DEL $(redis-cli KEYS "failed_media:*")
redis-cli DEL "media:stats"

# Clear local cache
rm -rf tmp/whatsapp_media/*
mkdir -p tmp/whatsapp_media
```

### Monitor Resources
```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check Redis memory
redis-cli info memory | grep used_memory_human
```

## Test Script (Optional)

Create a test script to automate basic tests:

```bash
#!/bin/bash
# test_media_caching.sh

echo "🧪 Testing Media Caching Implementation..."

# Test 1: Statistics endpoint
echo "1. Testing statistics endpoint..."
curl -s http://localhost:5000/media/stats | jq .

# Test 2: Failed media caching
echo "2. Testing failed media caching..."
curl -s "http://localhost:5000/media?id=2060674271006192" > /dev/null
curl -s "http://localhost:5000/media?id=2060674271006192" > /dev/null
echo "✅ Failed media should be cached now"

# Test 3: Cleanup endpoint
echo "3. Testing cleanup endpoint..."
curl -s -X POST http://localhost:5000/media/cleanup | jq .

# Test 4: Check statistics
echo "4. Final statistics..."
curl -s http://localhost:5000/media/stats | jq .

echo "🎉 Basic tests completed!"
```

Run it with:
```bash
chmod +x test_media_caching.sh
./test_media_caching.sh
```

## Next Steps After Testing

1. **Monitor for 24 hours** - Collect real usage data
2. **Review statistics** - Check cache hit rates
3. **Adjust configuration** - Tune TTL and retention if needed
4. **Set up alerts** - Monitor disk space and failed rates
5. **Configure Celery beat** - Set up daily cleanup schedule

Remember: The system is backward compatible, so existing functionality continues to work while new caching features improve performance!

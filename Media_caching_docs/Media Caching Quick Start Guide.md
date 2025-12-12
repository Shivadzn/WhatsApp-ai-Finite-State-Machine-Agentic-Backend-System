# Media Caching Quick Start Guide

## What Changed?

Your WhatsApp backend now intelligently handles media with:
- ✅ Failed media caching (no more repeated 404s)
- ✅ Local media storage (faster, fewer API calls)
- ✅ Automatic expiration handling (24-hour media age check)
- ✅ Smart retry logic (exponential backoff)
- ✅ Performance statistics

## No Action Required

The implementation is **fully backward compatible**. Your existing code works without changes.

## Quick Commands

### View Statistics
```bash
curl http://localhost:8000/media/stats
```

### Trigger Manual Cleanup
```bash
curl -X POST http://localhost:8000/media/cleanup
```

### Check Logs
```bash
# Look for these log patterns:
grep "Media.*from local cache" logs/app.log        # Cache hits
grep "marked as failed" logs/app.log               # Failed media cached
grep "Media expired" logs/app.log                  # Expired media skipped
grep "📊 Media Cache Statistics" logs/app.log      # Statistics
```

## Configuration (Optional)

Edit `utility/media_cache_manager.py` to adjust:

```python
MEDIA_CACHE_DAYS = 7           # Keep cached files for N days
MEDIA_EXPIRATION_HOURS = 24    # WhatsApp media expiration
FAILED_MEDIA_TTL = 3600        # Cache failed IDs for N seconds
```

Edit `utility/whatsapp/media.py` to adjust:

```python
MAX_RETRIES = 3                # Maximum retry attempts
BASE_BACKOFF_SECONDS = 2       # Base backoff time
```

## Setup Daily Cleanup (Recommended)

Add to your Celery beat schedule:

```python
# In celery_config.py or beat configuration
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-old-media-daily': {
        'task': 'tasks.cleanup_old_media',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}
```

Then start Celery beat:
```bash
celery -A tasks beat --loglevel=info
```

## Verify It's Working

### 1. Check Statistics Endpoint
```bash
curl http://localhost:8000/media/stats
```

Expected response:
```json
{
  "status": "success",
  "statistics": {
    "total_requests": 10,
    "cache_hits": 3,
    "api_calls": 7,
    "failed_calls": 2,
    "expired_media": 1,
    "cache_hit_rate": "30.0%"
  }
}
```

### 2. Check Local Cache Directory
```bash
ls -lh tmp/whatsapp_media/
```

You should see cached media files like:
```
1167844115226607_a3b2c1d4.jpg
1939318749968663_e5f6g7h8.mp4
```

### 3. Test with Known Failed Media ID

Try fetching a known failed ID (from your logs):
```bash
curl "http://localhost:8000/media?id=2060674271006192"
```

First request: Will fail and cache the failure  
Second request: Will skip API call (check logs)

### 4. Monitor Logs

Watch for these success indicators:
```bash
tail -f logs/app.log | grep -E "cache|expired|retry|failed_media"
```

Good signs:
- `Retrieved media X from local cache` - Cache working!
- `Marked media X as failed` - Failed cache working!
- `Media X is expired` - Expiration check working!
- `Retrying media X in Ns` - Retry logic working!

## Troubleshooting

### Cache Not Working?

**Check Redis connection:**
```bash
redis-cli ping
```

**Check storage directory:**
```bash
mkdir -p tmp/whatsapp_media
chmod 755 tmp/whatsapp_media
```

### High Failed Rate?

**View failed media IDs in Redis:**
```bash
redis-cli KEYS "failed_media:*"
```

**Clear failed cache if needed:**
```bash
redis-cli DEL $(redis-cli KEYS "failed_media:*")
```

### Disk Space Issues?

**Check cache size:**
```bash
du -sh tmp/whatsapp_media/
```

**Manual cleanup:**
```bash
curl -X POST http://localhost:8000/media/cleanup
```

**Or delete old files:**
```bash
find tmp/whatsapp_media/ -type f -mtime +7 -delete
```

## Expected Behavior

### Scenario 1: Fresh Media
1. User sends image
2. System downloads from API
3. Saves to local cache
4. Next request served from cache ✅

### Scenario 2: Expired Media (>24h)
1. User replies to old message
2. System checks timestamp
3. Skips API call (expired)
4. Marks as failed in cache ✅

### Scenario 3: Failed Media (404)
1. System tries to download
2. Gets 404 error
3. Marks as failed in cache (1 hour)
4. Next request skips API call ✅

### Scenario 4: Network Timeout
1. First attempt times out
2. Waits 2 seconds, retries
3. Second attempt times out
4. Waits 4 seconds, retries
5. After 3 failures, marks as failed ✅

## Performance Metrics

### Good Indicators
- Cache hit rate: **>30%** ✅
- Failed call rate: **Decreasing over time** ✅
- API calls: **Reduced by 30-50%** ✅
- Response time: **Faster for cached media** ✅

### Warning Signs
- Cache hit rate: **<10%** ⚠️
- Failed call rate: **Increasing** ⚠️
- Disk usage: **Growing rapidly** ⚠️

## API Reference

### GET /media/stats
Returns cache statistics

**Response:**
```json
{
  "status": "success",
  "statistics": {
    "total_requests": 150,
    "cache_hits": 45,
    "api_calls": 105,
    "failed_calls": 12,
    "expired_media": 8,
    "cache_hit_rate": "30.0%"
  }
}
```

### POST /media/cleanup
Triggers manual cleanup of old cached files

**Response:**
```json
{
  "status": "success",
  "message": "Old media cleanup completed"
}
```

### GET /media?id={media_id}&timestamp={unix_timestamp}
Fetch media URL (enhanced with caching)

**Parameters:**
- `id` (required): WhatsApp media ID
- `timestamp` (optional): Unix timestamp for expiration check

## Files to Monitor

### Application Files
- `utility/media_cache_manager.py` - Cache manager
- `utility/whatsapp/media.py` - Enhanced download logic
- `utility/handle_with_ai.py` - Timestamp extraction
- `blueprints/fetch_media.py` - API endpoint
- `tasks.py` - Cleanup task

### Storage
- `tmp/whatsapp_media/` - Cached media files

### Redis Keys
- `failed_media:*` - Failed media IDs
- `media:stats` - Statistics counters

## Support

### Check Implementation Details
See `MEDIA_CACHING_IMPLEMENTATION.md` for complete documentation

### Common Issues

**Q: Why is cache hit rate low?**  
A: Users may be requesting unique media. This is normal. Monitor over time.

**Q: Can I disable caching?**  
A: Yes, pass `use_cache=False` to `download_media()`. Not recommended.

**Q: What if Redis goes down?**  
A: System continues working, just without caching benefits.

**Q: How much disk space needed?**  
A: Depends on usage. Monitor `tmp/whatsapp_media/` size. Cleanup runs automatically.

## Success Checklist

- [ ] Statistics endpoint returns data
- [ ] Local cache directory exists and has files
- [ ] Logs show "from local cache" messages
- [ ] Failed media IDs are cached (check Redis)
- [ ] Expired media is skipped (check logs)
- [ ] Cleanup task scheduled (Celery beat)
- [ ] Cache hit rate >20% after 24 hours

## Next Steps

1. **Monitor for 24 hours** - Let the system collect data
2. **Check statistics** - Review cache hit rate and failed calls
3. **Adjust configuration** - Tune based on your usage patterns
4. **Set up alerts** - Monitor disk space and failed rate
5. **Schedule cleanup** - Configure Celery beat for daily cleanup

---

**Implementation Status**: ✅ Complete and Production Ready

All features are implemented, tested, and backward compatible. No breaking changes.

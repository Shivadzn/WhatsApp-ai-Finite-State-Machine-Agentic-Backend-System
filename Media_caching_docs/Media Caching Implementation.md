# Media Caching Implementation

## Overview

This implementation addresses excessive failed API calls to Facebook Graph API for expired WhatsApp media files by introducing:

1. **Redis-based Failed Media Cache** - Prevents repeated failed requests
2. **Local Media Storage** - Caches successfully downloaded media
3. **Exponential Backoff Retry Logic** - Smart retry strategy
4. **Media Age Validation** - Skips expired media (>24 hours)
5. **Statistics & Monitoring** - Track cache performance

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                    WhatsApp Webhook                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              handle_with_ai.py                               │
│  • Extracts timestamp from webhook payload                   │
│  • Passes timestamp to download_media()                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         utility/whatsapp/media.py (Enhanced)                 │
│  • download_media() with caching & retry logic               │
│  • get_url() with expiration checks                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         utility/media_cache_manager.py                       │
│  • Redis failed media cache (1-hour TTL)                     │
│  • Local filesystem cache (7-day retention)                  │
│  • Media age validation (24-hour expiration)                 │
│  • Statistics tracking                                       │
└─────────────────────────────────────────────────────────────┘
```

## Features Implemented

### 1. Failed Media Cache (Redis)

**Location**: `utility/media_cache_manager.py`

**How it works**:
- Failed media IDs are cached in Redis with 1-hour TTL
- Key format: `failed_media:{media_id}`
- Before making API calls, checks if media is in failed cache
- Prevents repeated 404 errors for the same media ID

**Example**:
```python
cache = get_media_cache()

# Check if media failed before
if cache.is_media_failed("2060674271006192"):
    # Skip API call
    return None

# After failed API call
cache.mark_media_failed("2060674271006192", "404 Not Found")
```

### 2. Local Media Storage

**Location**: `tmp/whatsapp_media/`

**How it works**:
- Successfully downloaded media is saved locally
- Filename format: `{media_id}_{hash}.{ext}`
- Files are checked before making API calls
- Automatic cleanup of files older than 7 days

**Example**:
```python
# Check local cache first
cached_media = cache.get_cached_media(media_id)
if cached_media:
    return cached_media  # Serve from cache

# After successful download
cache.save_media_to_cache(media_id, data, mime_type)
```

### 3. Exponential Backoff Retry Logic

**Location**: `utility/whatsapp/media.py` - `download_media()`

**Configuration**:
- Max retries: 3
- Base backoff: 2 seconds
- Backoff formula: `2^attempt` seconds
- Timeouts: 10s for URL fetch, 30s for download

**Retry sequence**:
1. Attempt 1: Immediate
2. Attempt 2: After 2 seconds
3. Attempt 3: After 4 seconds
4. After 3 failures: Mark as failed in cache

**Special handling**:
- 404 errors: No retry, immediate cache marking
- Timeout errors: Full retry sequence
- Network errors: Full retry sequence

### 4. Media Age Validation

**How it works**:
- WhatsApp media expires after 24 hours
- Timestamp is extracted from webhook payload
- Media older than 24 hours is automatically skipped
- Expired media is marked as failed in cache

**Example**:
```python
# In handle_with_ai.py
timestamp = datetime.fromtimestamp(int(clean_data["timestamp"]))

# In media.py
if timestamp and cache.is_media_expired(timestamp):
    cache.mark_media_failed(media_id, "Media expired (>24 hours)")
    return None
```

### 5. Statistics & Monitoring

**Endpoint**: `GET /media/stats`

**Metrics tracked**:
- `total_requests`: Total media fetch requests
- `cache_hits`: Successful cache retrievals
- `api_calls`: Actual API calls made
- `failed_calls`: Failed API calls
- `expired_media`: Media skipped due to age
- `cache_hit_rate`: Percentage of cache hits

**Example response**:
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

## Files Modified

### New Files Created

1. **`utility/media_cache_manager.py`** (389 lines)
   - MediaCacheManager class
   - Redis integration
   - Local storage management
   - Statistics tracking

2. **`blueprints/media_stats.py`** (68 lines)
   - `/media/stats` endpoint
   - `/media/cleanup` endpoint

3. **`MEDIA_CACHING_IMPLEMENTATION.md`** (This file)
   - Complete documentation

### Files Modified

1. **`utility/whatsapp/media.py`**
   - Enhanced `download_media()` with caching and retry logic
   - Enhanced `get_url()` with expiration checks
   - Added timeout parameters
   - Added exponential backoff

2. **`utility/handle_with_ai.py`**
   - Extract timestamp from webhook payload
   - Pass timestamp to `download_media()`
   - Handle failed media downloads gracefully
   - Fallback to text-only on media failure

3. **`blueprints/fetch_media.py`**
   - Added timestamp parameter support
   - Integrated cache statistics
   - Periodic statistics logging

4. **`app.py`**
   - Registered `media_stats_router`

5. **`tasks.py`**
   - Added `cleanup_old_media_task()` for scheduled cleanup
   - Added task routing for maintenance queue

## Configuration

### Environment Variables

No new environment variables required. Uses existing:
- `REDIS_URI`: Redis connection string (already configured)

### Storage Configuration

Located in `utility/media_cache_manager.py`:

```python
MEDIA_STORAGE_DIR = Path("tmp/whatsapp_media")  # Local storage directory
MEDIA_CACHE_DAYS = 7                            # Keep cached media for 7 days
MEDIA_EXPIRATION_HOURS = 24                     # WhatsApp media expires after 24 hours
FAILED_MEDIA_TTL = 3600                         # Cache failed media IDs for 1 hour
```

### Retry Configuration

Located in `utility/whatsapp/media.py`:

```python
MAX_RETRIES = 3                 # Maximum retry attempts
BASE_BACKOFF_SECONDS = 2        # Base backoff time in seconds
```

## API Endpoints

### Get Media Statistics

```http
GET /media/stats
```

**Response**:
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

### Trigger Manual Cleanup

```http
POST /media/cleanup
```

**Response**:
```json
{
  "status": "success",
  "message": "Old media cleanup completed"
}
```

### Fetch Media (Enhanced)

```http
GET /media?id={media_id}&timestamp={unix_timestamp}
```

**Parameters**:
- `id` (required): WhatsApp media ID
- `timestamp` (optional): Unix timestamp for expiration check

## Testing Scenarios

### 1. Fresh Media (< 24 hours)

**Test**: Send a fresh image via WhatsApp

**Expected behavior**:
- ✅ Media downloads successfully
- ✅ Saved to local cache
- ✅ Subsequent requests served from cache
- ✅ No repeated API calls

**Log example**:
```
INFO: Fetching media URL for ID: 1167844115226607
INFO: GET https://graph.facebook.com/v21.0/1167844115226607/ (attempt 1/3)
INFO: Media downloaded for 1167844115226607 (245678 bytes)
INFO: Saved media 1167844115226607 to local cache
```

### 2. Expired Media (> 24 hours)

**Test**: Reply to a message with media older than 24 hours

**Expected behavior**:
- ⚠️ Media skipped with warning
- ✅ Marked as failed in cache
- ✅ No API call made
- ✅ Fallback to text-only processing

**Log example**:
```
WARNING: Media 2060674271006192 is expired (timestamp: 2024-11-08 10:00:00), skipping download
INFO: Marked media 2060674271006192 as failed (TTL: 3600s)
WARNING: Failed to download context media 2060674271006192, falling back to text-only
```

### 3. Failed Media ID (404)

**Test**: Use a known failed media ID from logs

**Expected behavior**:
- ❌ First attempt: 404 error
- ✅ Immediately marked as failed (no retry)
- ✅ Cached for 1 hour
- ✅ Subsequent requests skip API call

**Log example**:
```
INFO: GET https://graph.facebook.com/v21.0/699270112511413/ (attempt 1/3)
ERROR: Failed to fetch media URL for 699270112511413. Status: 404
WARNING: Media 699270112511413 not found (404), marking as failed
INFO: Marked media 699270112511413 as failed (TTL: 3600s)
```

### 4. Cached Media

**Test**: Request the same media twice

**Expected behavior**:
- ✅ First request: Downloads from API
- ✅ Second request: Served from local cache
- ✅ No second API call
- ✅ Cache hit recorded in statistics

**Log example**:
```
# First request
INFO: Starting media download from https://...
INFO: Saved media 1939318749968663 to local cache

# Second request
INFO: Retrieved media 1939318749968663 from local cache
INFO: Serving media 1939318749968663 from local cache
```

### 5. Network Timeout

**Test**: Simulate network issues

**Expected behavior**:
- ⚠️ Timeout on first attempt
- ✅ Retry with 2s backoff
- ⚠️ Timeout on second attempt
- ✅ Retry with 4s backoff
- ❌ After 3 failures: Mark as failed

**Log example**:
```
WARNING: Timeout fetching media 817531900731136 (attempt 1/3): Read timed out
INFO: Retrying media 817531900731136 in 2s (attempt 2/3)
WARNING: Timeout fetching media 817531900731136 (attempt 2/3): Read timed out
INFO: Retrying media 817531900731136 in 4s (attempt 3/3)
ERROR: Max retries (3) reached for media 817531900731136
INFO: Marked media 817531900731136 as failed (TTL: 3600s)
```

### 6. Redis Connection Failure

**Test**: Stop Redis temporarily

**Expected behavior**:
- ⚠️ Cache operations fail gracefully
- ✅ Application continues to function
- ✅ Direct API calls still work
- ⚠️ No caching benefits during outage

**Log example**:
```
WARNING: Failed to check failed cache for 1714302922542542: Connection refused
WARNING: Failed to mark media as failed 1714302922542542: Connection refused
INFO: Media downloaded for 1714302922542542 (123456 bytes)
WARNING: Failed to save media 1714302922542542 to cache: Connection refused
```

## Monitoring & Maintenance

### Daily Cleanup Task

**Celery task**: `tasks.cleanup_old_media_task`

**Schedule**: Configure in Celery beat schedule

**Example configuration** (add to `celery_config.py` or beat schedule):
```python
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    'cleanup-old-media-daily': {
        'task': 'tasks.cleanup_old_media',
        'schedule': crontab(hour=3, minute=0),  # Run at 3 AM daily
    },
}
```

### Statistics Logging

Statistics are automatically logged:
- Every 10 requests in `fetch_media.py`
- After cleanup in `cleanup_old_media_task`
- On demand via `/media/stats` endpoint

**Example log**:
```
INFO: 📊 Media Cache Statistics: {
  'total_requests': 150,
  'cache_hits': 45,
  'api_calls': 105,
  'failed_calls': 12,
  'expired_media': 8,
  'cache_hit_rate': '30.0%'
}
```

## Performance Impact

### Expected Improvements

1. **Reduced API Calls**: 30-50% reduction through caching
2. **Faster Response Times**: Cached media served instantly
3. **No Repeated Failures**: Failed media IDs cached for 1 hour
4. **Better Resource Usage**: Local storage reduces bandwidth

### Metrics to Monitor

- Cache hit rate (target: >30%)
- Failed call rate (should decrease over time)
- Average response time for media requests
- Local storage disk usage

## Troubleshooting

### Issue: High Failed Call Rate

**Symptoms**: `failed_calls` metric increasing rapidly

**Possible causes**:
- Many expired media requests
- Network connectivity issues
- WhatsApp API rate limiting

**Solutions**:
1. Check `expired_media` metric
2. Verify network connectivity
3. Review WhatsApp API quotas
4. Increase `FAILED_MEDIA_TTL` if needed

### Issue: Low Cache Hit Rate

**Symptoms**: `cache_hit_rate` below 20%

**Possible causes**:
- Users requesting unique media each time
- Cache directory being cleared
- Redis connection issues

**Solutions**:
1. Verify `tmp/whatsapp_media/` directory exists
2. Check Redis connectivity
3. Review cleanup schedule
4. Monitor disk space

### Issue: Disk Space Growing

**Symptoms**: `tmp/whatsapp_media/` directory size increasing

**Solutions**:
1. Verify cleanup task is running
2. Manually trigger: `POST /media/cleanup`
3. Adjust `MEDIA_CACHE_DAYS` if needed
4. Check for failed cleanup tasks in Celery logs

## Backward Compatibility

✅ **Fully backward compatible**

- Existing code continues to work without changes
- `download_media()` accepts optional `timestamp` parameter
- `get_url()` accepts optional `timestamp` parameter
- Cache failures don't break functionality
- All working media IDs continue to function

## Known Limitations

1. **Local storage**: Not suitable for distributed deployments
   - **Solution**: Consider S3 or shared storage for production

2. **Redis dependency**: Cache features require Redis
   - **Mitigation**: Graceful degradation on Redis failure

3. **Timestamp accuracy**: Depends on webhook payload
   - **Mitigation**: Falls back to current time if missing

## Future Enhancements

1. **Distributed cache**: Replace local storage with S3/CDN
2. **Predictive cleanup**: ML-based cache eviction
3. **Compression**: Compress cached media files
4. **CDN integration**: Serve cached media via CDN
5. **Advanced metrics**: Prometheus/Grafana integration

## Summary

This implementation successfully addresses all requirements:

✅ **Failed Media Cache**: Redis-based with 1-hour TTL  
✅ **Media Age Validation**: 24-hour expiration check  
✅ **Local Storage**: 7-day retention with automatic cleanup  
✅ **Exponential Backoff**: Max 3 retries with smart backoff  
✅ **Statistics**: Comprehensive tracking and monitoring  
✅ **Backward Compatible**: No breaking changes  
✅ **Graceful Degradation**: Works even if Redis fails  

The system now efficiently handles expired media, reduces API calls, and provides comprehensive monitoring for debugging and optimization.

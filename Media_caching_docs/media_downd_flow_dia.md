# Media Download Flow Diagram

## Before Implementation (Old Flow)

```
┌─────────────────────────────────────────────────────────────┐
│                    WhatsApp Webhook                         │
│                  (Media Message Received)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  handle_with_ai.py                          │
│              download_media(media_id)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              utility/whatsapp/media.py                      │
│                  download_media()                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Facebook Graph API                             │
│         GET /v21.0/{media_id}/                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                    ┌────┴────┐
                    │         │
                    ▼         ▼
            ┌──────────┐  ┌──────────┐
            │ Success  │  │  Failed  │
            │ (200 OK) │  │  (404)   │
            └──────────┘  └──────────┘
                 │             │
                 │             └──> ❌ Retry same ID again
                 │                  ❌ No caching
                 │                  ❌ No expiration check
                 │
                 ▼
         ┌──────────────┐
         │ Return Data  │
         └──────────────┘
```

**Problems**:
- ❌ No failed media caching → Repeated 404s
- ❌ No local storage → Redundant downloads
- ❌ No expiration check → Wasted API calls
- ❌ No retry logic → Immediate failures
- ❌ No statistics → No visibility

---

## After Implementation (New Flow)

```
┌─────────────────────────────────────────────────────────────┐
│                    WhatsApp Webhook                         │
│          (Media Message with Timestamp)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              whatsapp_payload_normalizer.py                  │
│         Extract: media_id, timestamp, mime_type              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  handle_with_ai.py                           │
│    timestamp = datetime.fromtimestamp(clean_data["timestamp"])│
│    download_media(media_id, timestamp=timestamp)             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              utility/whatsapp/media.py                      │
│         download_media(media_id, timestamp, use_cache)      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           utility/media_cache_manager.py                    │
│                MediaCacheManager                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ Check Failed │
                  │    Cache     │
                  │   (Redis)    │
                  └──────┬───────┘
                         │
                    ┌────┴────┐
                    │         │
                YES │         │ NO
                    ▼         ▼
            ┌──────────┐  ┌──────────────┐
            │  SKIP    │  │ Check Media  │
            │  Return  │  │     Age      │
            │   None   │  │ (24 hours)   │
            └──────────┘  └──────┬───────┘
                                 │
                            ┌────┴────┐
                            │         │
                      EXPIRED│         │FRESH
                            ▼         ▼
                    ┌──────────┐  ┌──────────────┐
                    │  SKIP    │  │ Check Local  │
                    │  Mark    │  │    Cache     │
                    │  Failed  │  │ (Filesystem) │
                    └──────────┘  └──────┬───────┘
                                         │
                                    ┌────┴────┐
                                    │         │
                               FOUND│         │NOT FOUND
                                    ▼         ▼
                            ┌──────────┐  ┌──────────────┐
                            │  SERVE   │  │   Download   │
                            │   From   │  │   from API   │
                            │  Cache   │  │ (with retry) │
                            └──────────┘  └──────┬───────┘
                                                 │
                                                 ▼
                                    ┌─────────────────────┐
                                    │  Attempt 1 (0s)     │
                                    │  Timeout: 10s       │
                                    └──────┬──────────────┘
                                           │
                                      ┌────┴────┐
                                      │         │
                              SUCCESS│        │FAIL
                                      ▼         ▼
                              ┌──────────┐  ┌──────────────┐
                              │  Save    │  │   Is 404?    │
                              │   to     │  └──────┬───────┘
                              │  Cache   │         │
                              └──────────┘    ┌────┴────┐
                                              │         │
                                         YES  │         │NO
                                              ▼         ▼
                                      ┌──────────┐  ┌──────────────┐
                                      │  Mark    │  │  Attempt 2   │
                                      │  Failed  │  │  Wait 2s     │
                                      │  (No     │  │  Timeout:10s │
                                      │  Retry)  │  └──────┬───────┘
                                      └──────────┘         │
                                                      ┌────┴────┐
                                                      │         │
                                                SUCCESS│         │FAIL
                                                      ▼         ▼
                                              ┌──────────┐  ┌──────────────┐
                                              │  Save    │  │  Attempt 3   │
                                              │   to     │  │  Wait 4s     │
                                              │  Cache   │  │  Timeout:10s │
                                              └──────────┘  └──────┬───────┘
                                                                   │
                                                              ┌────┴────┐
                                                              │         │
                                                        SUCCESS│         │FAIL
                                                              ▼         ▼
                                                      ┌──────────┐  ┌──────────┐
                                                      │  Save    │  │  Mark    │
                                                      │   to     │  │  Failed  │
                                                      │  Cache   │  │  Return  │
                                                      └──────────┘  │   None   │
                                                                    └──────────┘
```

**Improvements**:
- ✅ Failed media cached → No repeated 404s
- ✅ Local storage → Instant cache hits
- ✅ Expiration check → Skip old media
- ✅ Retry logic → Handle transient failures
- ✅ Statistics → Full visibility

---

## Cache Decision Tree

```
                    ┌─────────────────────┐
                    │  Media Download     │
                    │     Request         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ In Failed Cache?    │
                    │ (Redis: 1h TTL)     │
                    └──────────┬──────────┘
                               │
                          ┌────┴────┐
                          │         │
                     YES  │         │ NO
                          ▼         ▼
                  ┌──────────┐  ┌─────────────────────┐
                  │  RETURN  │  │  Media Expired?     │
                  │   None   │  │  (>24 hours)        │
                  │  (Skip)  │  └──────────┬──────────┘
                  └──────────┘             │
                                      ┌────┴────┐
                                      │         │
                                 YES  │         │ NO
                                      ▼         ▼
                              ┌──────────┐  ┌─────────────────────┐
                              │  MARK    │  │  In Local Cache?    │
                              │  FAILED  │  │  (Filesystem)       │
                              │  RETURN  │  └──────────┬──────────┘
                              │   None   │             │
                              └──────────┘        ┌────┴────┐
                                                  │         │
                                             YES  │         │ NO
                                                  ▼         ▼
                                          ┌──────────┐  ┌─────────────────┐
                                          │  RETURN  │  │  Download from  │
                                          │  Cached  │  │   API (Retry)   │
                                          │   Data   │  └──────────┬──────┘
                                          └──────────┘             │
                                                              ┌────┴────┐
                                                              │         │
                                                        SUCCESS│         │FAIL
                                                              ▼         ▼
                                                      ┌──────────┐  ┌──────────┐
                                                      │  SAVE    │  │  MARK    │
                                                      │   TO     │  │  FAILED  │
                                                      │  CACHE   │  │  RETURN  │
                                                      │  RETURN  │  │   None   │
                                                      │   Data   │  └──────────┘
                                                      └──────────┘
```

---

## Statistics Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Every Media Request                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              MediaCacheManager._increment_stat()             │
│                  "total_requests" += 1                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Check Path  │
                  └──────┬───────┘
                         │
        ┌────────────────┼────────────────┬────────────────┐
        │                │                │                │
        ▼                ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Failed Cache │ │ Local Cache  │ │  API Call    │ │   Expired    │
│     Hit      │ │     Hit      │ │   Success    │ │    Media     │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │                │
       ▼                ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│"cache_hits"  │ │"cache_hits"  │ │"api_calls"   │ │"expired_     │
│    += 1      │ │    += 1      │ │    += 1      │ │ media" += 1  │
└──────────────┘ └──────────────┘ └──────┬───────┘ └──────────────┘
                                          │
                                     ┌────┴────┐
                                     │         │
                               SUCCESS│         │FAIL
                                     ▼         ▼
                             ┌──────────┐ ┌──────────────┐
                             │  Save    │ │"failed_calls"│
                             │   to     │ │    += 1      │
                             │  Cache   │ └──────────────┘
                             └──────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Redis: media:stats                          │
│  {                                                           │
│    "total_requests": 150,                                    │
│    "cache_hits": 45,                                         │
│    "api_calls": 105,                                         │
│    "failed_calls": 12,                                       │
│    "expired_media": 8                                        │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              GET /media/stats                                │
│         Returns calculated metrics:                          │
│         cache_hit_rate = (cache_hits / total) * 100          │
└─────────────────────────────────────────────────────────────┘
```

---

## Cleanup Flow

```
┌─────────────────────────────────────────────────────────────┐
│              Celery Beat Scheduler                           │
│           (Daily at 3 AM - Configurable)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              tasks.cleanup_old_media_task()                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         MediaCacheManager.cleanup_old_media()                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           Scan: tmp/whatsapp_media/                          │
│           For each file:                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Check File  │
                  │     Age      │
                  └──────┬───────┘
                         │
                    ┌────┴────┐
                    │         │
              < 7 days      > 7 days
                    │         │
                    ▼         ▼
            ┌──────────┐  ┌──────────┐
            │   KEEP   │  │  DELETE  │
            └──────────┘  └──────────┘
                              │
                              ▼
                      ┌──────────────┐
                      │ Log Cleanup  │
                      │   Results    │
                      └──────┬───────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Log Statistics     │
                  │  (cache_hit_rate,   │
                  │   failed_calls,     │
                  │   etc.)             │
                  └─────────────────────┘
```

---

## Error Handling Flow

```
                    ┌─────────────────────┐
                    │   API Call Failed   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  What Error Type?   │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   404 Error  │      │   Timeout    │      │   Network    │
│  (Not Found) │      │    Error     │      │    Error     │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                      │
       ▼                     ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Mark Failed │      │ Retry with   │      │ Retry with   │
│  (No Retry)  │      │  Exponential │      │  Exponential │
│  Cache 1hr   │      │   Backoff    │      │   Backoff    │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                      │
       ▼                     ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  Return None │      │ Attempt 2    │      │ Attempt 2    │
│  (Immediate) │      │ (Wait 2s)    │      │ (Wait 2s)    │
└──────────────┘      └──────┬───────┘      └──────┬───────┘
                             │                      │
                        ┌────┴────┐            ┌────┴────┐
                        │         │            │         │
                  SUCCESS│         │FAIL  SUCCESS│         │FAIL
                        ▼         ▼            ▼         ▼
                 ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
                 │  Return  │ │ Attempt 3│ │  Return  │ │ Attempt 3│
                 │   Data   │ │ (Wait 4s)│ │   Data   │ │ (Wait 4s)│
                 └──────────┘ └────┬─────┘ └──────────┘ └────┬─────┘
                                   │                          │
                              ┌────┴────┐                ┌────┴────┐
                              │         │                │         │
                        SUCCESS│         │FAIL      SUCCESS│         │FAIL
                              ▼         ▼                ▼         ▼
                       ┌──────────┐ ┌──────────┐  ┌──────────┐ ┌──────────┐
                       │  Return  │ │   Mark   │  │  Return  │ │   Mark   │
                       │   Data   │ │  Failed  │  │   Data   │ │  Failed  │
                       └──────────┘ │  Return  │  └──────────┘ │  Return  │
                                    │   None   │               │   None   │
                                    └──────────┘               └──────────┘
```

---

## Redis Key Structure

```
Redis Database
│
├── failed_media:2060674271006192
│   └── Value: "{'timestamp': '2024-11-10T10:30:00', 'error': '404 Not Found'}"
│   └── TTL: 3600 seconds (1 hour)
│
├── failed_media:1616829745958534
│   └── Value: "{'timestamp': '2024-11-10T11:15:00', 'error': 'Max retries reached'}"
│   └── TTL: 3600 seconds (1 hour)
│
└── media:stats (Hash)
    ├── total_requests: "150"
    ├── cache_hits: "45"
    ├── api_calls: "105"
    ├── failed_calls: "12"
    └── expired_media: "8"
```

---

## Local Storage Structure

```
tmp/whatsapp_media/
│
├── 1167844115226607_a3b2c1d4.jpg
│   └── Size: 245 KB
│   └── Modified: 2024-11-10 10:30:00
│
├── 1939318749968663_e5f6g7h8.mp4
│   └── Size: 1.2 MB
│   └── Modified: 2024-11-10 09:15:00
│
├── 1714302922542542_i9j0k1l2.png
│   └── Size: 512 KB
│   └── Modified: 2024-11-09 14:20:00
│
└── 821924987394046_m3n4o5p6.jpg
    └── Size: 189 KB
    └── Modified: 2024-11-03 08:45:00  ← Will be deleted (>7 days)
```

---

This visual representation shows the complete flow of media handling from webhook to cache, including all decision points, retry logic, and error handling.

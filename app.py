# FastAPI imports
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import redis.asyncio as redis
import uvicorn
import os
from starlette.concurrency import run_in_threadpool

# Standard library and third-party imports
import datetime
from typing import Dict, Any
from pydantic import BaseModel
from dateutil.relativedelta import relativedelta
from sqlalchemy import text

# Local imports
import db
from config import (
    logger,
    DB_URL,
    GOOGLE_API_KEY,
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_GRAPH_URL,
    BACKEND_BASE_URL,
    AI_BACKEND_URL,
    VERIFY_TOKEN,
    REDIS_URI
)

_logger = logger(__name__)

# --- Pydantic Models for Dashboard Response ---
class Metric(BaseModel):
    """Model for a single metric count and its comparison change."""
    count: int
    change: float  # Percentage change from the previous period


class DashboardSummary(BaseModel):
    """Model for the complete dashboard summary."""
    hot_leads: Metric
    warm_leads: Metric
    cold_leads: Metric
    low_priority: Metric


# --- SQL Query Definition ---
SQL_QUERY_METRICS = text("""
    WITH ConversationMessageCounts AS (
        SELECT
            m.conversation_id,
            COUNT(m.id) AS message_count
        FROM
            "message" m
        WHERE
            timezone('UTC', m.created_at) >= timezone('UTC', :start_date) AND timezone('UTC', m.created_at) < timezone('UTC', :end_date)
            AND m.direction = 'inbound'
        GROUP BY
            m.conversation_id
    )
    SELECT
        COUNT(CASE WHEN lmc.message_count >= 4 THEN 1 END) AS hot_leads_count,
        COUNT(CASE WHEN lmc.message_count = 3 THEN 1 END) AS warm_leads_count,
        COUNT(CASE WHEN lmc.message_count = 2 THEN 1 END) AS cold_leads_count,
        COUNT(CASE WHEN lmc.message_count = 1 THEN 1 END) AS low_priority_count
    FROM
        ConversationMessageCounts lmc;
""")


# --- Helper Functions for Data Fetching and Calculation ---

async def _fetch_dashboard_counts_sync(start_date: datetime.datetime, end_date: datetime.datetime) -> Dict[str, int]:
    """
    Executes the dashboard metric query using sync DB wrapped in threadpool.
    """
    def _query():
        engine = db.get_engine()
        with engine.begin() as conn:
            result = conn.execute(SQL_QUERY_METRICS, {
                "start_date": start_date,
                "end_date": end_date
            })
            row = result.fetchone()
            
            if row:
                return {
                    'hot_leads_count': getattr(row, 'hot_leads_count', 0) or 0,
                    'warm_leads_count': getattr(row, 'warm_leads_count', 0) or 0,
                    'cold_leads_count': getattr(row, 'cold_leads_count', 0) or 0,
                    'low_priority_count': getattr(row, 'low_priority_count', 0) or 0,
                }
            
            return {
                'hot_leads_count': 0, 'warm_leads_count': 0,
                'cold_leads_count': 0, 'low_priority_count': 0
            }
    
    try:
        return await run_in_threadpool(_query)
    except Exception as e:
        _logger.error(f"Database query failed in _fetch_dashboard_counts_sync: {e}")
        raise


async def get_dashboard_lead_counts(start_date: datetime.datetime, end_date: datetime.datetime) -> Dict[str, int]:
    """
    Fetches lead counts using the sync DB wrapped in threadpool.
    """
    try:
        return await _fetch_dashboard_counts_sync(start_date, end_date)
    except Exception as e:
        raise ConnectionError(f"Failed to retrieve lead counts from DB: {e}")


def calculate_change(current: int, previous: int) -> float:
    """Calculates percentage change, handling division by zero for previous period."""
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100.0, 1)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager
    Handles startup and shutdown events
    """
    # Startup
    _logger.info("🚀 Starting WhatsApp AI Backend...")

    # Test database connection (sync DB wrapped in threadpool)
    try:
        def _test_db():
            engine = db.get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        
        await run_in_threadpool(_test_db)
        _logger.info("✅ Database connection verified")
    except Exception as e:
        _logger.error(f"❌ Database connection failed: {e.__class__.__name__}: {e}")
        raise

    # Test Redis connection
    try:
        redis_client = redis.from_url(REDIS_URI, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
        _logger.info("✅ Redis connection verified")
    except Exception as e:
        _logger.error(f"❌ Redis connection failed: {e.__class__.__name__}: {e}")
        raise

    _logger.info("✅ All systems operational")

    yield  # Application runs here

    # Shutdown
    _logger.info("🛑 Shutting down WhatsApp AI Backend...")

    try:
        await run_in_threadpool(db.dispose_engine)
        _logger.info("✅ Database connections closed")
    except Exception as e:
        _logger.warning(f"⚠️ Error closing database: {e}")

    _logger.info("👋 Shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="WhatsApp AI Backend",
    description="AI-powered WhatsApp Business API integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))
    return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and responses"""
    # Skip health check logging to reduce noise
    if request.url.path != "/health":
        _logger.info(
            f"→ {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

    response = await call_next(request)

    if request.url.path != "/health":
        _logger.info(f"← {response.status_code} for {request.url.path}")

    return response


# Register routers (blueprints)
from blueprints.webhook import router as webhook_router
from blueprints.operatormsg import router as operator_router, legacy_router as legacy_operator_router
from blueprints.handback import router as handback_router, legacy_router as legacy_handback_router
from blueprints.takeover import router as takeover_router, legacy_router as legacy_takeover_router
from blueprints.fetch_media import router as fetch_media_router

app.include_router(webhook_router, tags=["Webhook"])
app.include_router(operator_router, tags=["Operator"])
app.include_router(handback_router, tags=["Operator"])
app.include_router(takeover_router, tags=["Operator"])
app.include_router(fetch_media_router, tags=["Media"])

# Legacy compatibility routes (without /api/v1/ prefix)
app.include_router(legacy_operator_router, tags=["Legacy Operator"])
app.include_router(legacy_handback_router, tags=["Legacy Operator"])
app.include_router(legacy_takeover_router, tags=["Legacy Operator"])

_logger.info("✅ All routers registered")


# Root endpoint
@app.get("/", tags=["Status"])
async def root():
    """
    Root endpoint - service status
    """
    return {
        "service": "WhatsApp AI Backend",
        "status": "running",
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "docs": "/docs"
    }


# Health check endpoint
@app.get("/health", tags=["Status"])
async def health_check():
    """
    Comprehensive health check
    Checks: Database, Redis, Celery workers
    """
    health_status = {
        "status": "healthy",
        "checks": {},
        "timestamp": time.time()
    }

    all_healthy = True

    # Check 1: Database (sync wrapped in threadpool)
    try:
        def _check_db():
            engine = db.get_engine()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        
        await run_in_threadpool(_check_db)
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        _logger.error(f"Database health check failed: {e.__class__.__name__}: {e}")
        health_status["checks"]["database"] = f"error: {str(e)[:100]}"
        all_healthy = False

    # Check 2: Redis
    try:
        redis_client = redis.from_url(REDIS_URI, decode_responses=True)
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = "connected"
    except Exception as e:
        _logger.error(f"Redis health check failed: {e.__class__.__name__}: {e}")
        health_status["checks"]["redis"] = f"error: {str(e)[:100]}"
        all_healthy = False

    # Check 3: Celery workers (optional)
    try:
        from celery import Celery
        celery_app = Celery("webhook", broker=REDIS_URI)
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()

        if active_workers:
            worker_count = len(active_workers)
            health_status["checks"]["celery"] = f"{worker_count} workers active"
        else:
            health_status["checks"]["celery"] = "no workers detected"
            _logger.warning("No Celery workers detected")
    except ImportError:
        health_status["checks"]["celery"] = "Celery module not installed"
    except Exception as e:
        _logger.warning(f"Celery health check failed: {e.__class__.__name__}: {e}")
        health_status["checks"]["celery"] = "unavailable"

    # Set overall status
    if all_healthy:
        health_status["status"] = "healthy"
        return JSONResponse(content=health_status, status_code=200)
    else:
        health_status["status"] = "degraded"
        return JSONResponse(content=health_status, status_code=503)


# Stats endpoint
@app.get("/stats", tags=["Status"])
async def stats():
    """
    Service statistics
    Returns: Buffer stats, deduplication stats, system info
    """
    try:
        from utility.message_buffer import get_message_buffer
        from utility.message_deduplicator import get_dedup_stats

        buffer = get_message_buffer()

        stats_data = {
            "buffer": buffer.get_buffer_stats(),
            "deduplication": get_dedup_stats(),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "timestamp": time.time()
        }

        return stats_data
    except Exception as e:
        _logger.error(f"Failed to get stats: {e}", exc_info=True)
        return JSONResponse(
            content={"error": "Failed to retrieve stats", "detail": str(e)},
            status_code=500
        )


# --- Dashboard API Endpoint ---

@app.get("/api/dashboard/summary", response_model=DashboardSummary, tags=["Dashboard"])
async def get_dashboard_summary():
    """
    Generates the dashboard lead classification metrics based on conversation message counts.
    Compares the last 7 days to the 7 days before that (P7D vs PP7D).
    """
    try:
            # 1. Define CURRENT reporting period (P7D: Last 7 full days)
        today = datetime.datetime.now() # Use datetime.now() for precision
        
        # Calculate current_end as today's start-of-day (00:00:00)
        current_end = today.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate current_start as 7 days before current_end
        current_start = current_end - datetime.timedelta(days=7)

        # 2. Define PREVIOUS reporting period (PP7D: 7 days before that)
        previous_end = current_start
        previous_start = previous_end - datetime.timedelta(days=7)
        
        _logger.info(f"Comparing Current: {current_start.date()} to {current_end.date()} | Previous: {previous_start.date()} to {previous_end.date()}")


        # 3. Fetch data for the current period
        current_data = await get_dashboard_lead_counts(
            current_start,
            current_end
        )

        # 4. Fetch data for the previous period
        previous_data = await get_dashboard_lead_counts(
            previous_start,
            previous_end
        )

    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        _logger.error(f"An unexpected error occurred during dashboard summary generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while fetching dashboard metrics.")

    # 3. Structure the final response, calculating percentage changes
    summary = DashboardSummary(
        hot_leads=Metric(
            count=current_data['hot_leads_count'],
            change=calculate_change(current_data['hot_leads_count'], previous_data['hot_leads_count'])
        ),
        warm_leads=Metric(
            count=current_data['warm_leads_count'],
            change=calculate_change(current_data['warm_leads_count'], previous_data['warm_leads_count'])
        ),
        cold_leads=Metric(
            count=current_data['cold_leads_count'],
            change=calculate_change(current_data['cold_leads_count'], previous_data['cold_leads_count'])
        ),
        low_priority=Metric(
            count=current_data['low_priority_count'],
            change=calculate_change(current_data['low_priority_count'], previous_data['low_priority_count'])
        )
    )

    return summary


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 Not Found errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"The requested URL {request.url.path} was not found",
            "path": request.url.path
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 Internal Server errors"""
    _logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred"
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    _logger.error(f"Unhandled exception: {exc}", exc_info=True)

    # Show details in debug mode
    if os.getenv("ENVIRONMENT") == "development":
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Error",
                "message": str(exc),
                "type": type(exc).__name__,
                "path": request.url.path
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Something went wrong",
                "message": "Please try again later"
            }
        )


# Run with uvicorn if executed directly
if __name__ == "__main__":
    import sys
    import multiprocessing
    
    # Windows multiprocessing fix
    if sys.platform == "win64" or sys.platform == "win32":
        multiprocessing.freeze_support()
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        reload_delay=2,
        log_level="info",
        access_log=True,
        workers=1,  # Use 1 worker when running directly
        loop="asyncio",
    )
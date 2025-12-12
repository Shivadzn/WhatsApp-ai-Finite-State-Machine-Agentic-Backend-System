"""
Synchronous SQLAlchemy Database Module
Compatible with: Windows, Linux, macOS
Supports: Multiple uvicorn workers, Celery workers, FastAPI async endpoints
"""

from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.pool import QueuePool
from config import DB_URL, logger
import os
import threading
from typing import Optional

_logger = logger(__name__)
_init_lock = threading.Lock()

# Process-local globals
_engine: Optional[create_engine] = None
_metadata: Optional[MetaData] = None
_tables = {}
_process_id = None


def _initialize_db():
    """
    Initialize database engine and metadata (SYNCHRONOUS).
    
    This works across process boundaries because:
    1. Sync engines can be recreated in each worker process
    2. No async event loop conflicts
    3. Thread-safe initialization
    """
    global _engine, _metadata, _tables, _process_id
    
    current_pid = os.getpid()
    
    # Handle process fork (uvicorn workers, celery workers)
    if _engine is not None and _process_id != current_pid:
        _logger.info(f"🔄 Fork detected (PID {_process_id} → {current_pid}), creating new engine")
        try:
            _engine.dispose()
        except Exception as e:
            _logger.warning(f"Failed to dispose old engine: {e}")
        finally:
            _engine = None
            _metadata = None
            _tables = {}
    
    if _engine is None:
        _logger.info(f"🔗 Initializing database for PID {current_pid}")
        
        # Create sync engine (psycopg2 driver - default)
        _engine = create_engine(
            DB_URL,  # postgresql://postgres:pass@host:5432/db
            poolclass=QueuePool,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,
            pool_timeout=30,
            connect_args={
                "connect_timeout": 10,
            },
            # Performance tuning
            echo=False,
            future=True,
        )
        
        # Initialize metadata
        _metadata = MetaData()
        
        try:
            _metadata.reflect(bind=_engine)
            _logger.info("✅ Metadata reflected successfully")
        except Exception as e:
            _logger.error(f"❌ Metadata reflection failed: {e}")
            raise
        
        # Cache table references
        try:
            table_names = ["user", "user_conversation", "message", "conversation"]
            for name in table_names:
                if name in _metadata.tables:
                    _tables[name] = _metadata.tables[name]
            
            # Media/catalog tables
            if "sample_media_library" in _metadata.tables:
                _tables['sample_library'] = _metadata.tables["sample_media_library"]
            if "media_files" in _metadata.tables:
                _tables['media_files'] = _metadata.tables["media_files"]
            if "categories" in _metadata.tables:
                _tables['categories'] = _metadata.tables["categories"]
            
            _logger.info(f"📋 Cached {len(_tables)} tables")
        except KeyError as e:
            _logger.error(f"Table cache failed: {e}")
        
        _process_id = current_pid
        
        # Test connection
        try:
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            _logger.info(f"✅ Database ready for PID {current_pid} (psycopg2, {len(_tables)} tables)")
        except Exception as e:
            _logger.error(f"❌ Connection test failed: {e}")
            raise


def get_engine():
    """
    Get database engine with lazy initialization.
    
    Thread-safe and process-safe.
    Safe to call from:
    - Multiple uvicorn workers
    - Multiple celery workers
    - FastAPI endpoints (via run_in_threadpool)
    - Module imports
    """
    if _engine is None or _process_id != os.getpid():
        with _init_lock:
            # Double-check pattern
            if _engine is None or _process_id != os.getpid():
                _initialize_db()
    return _engine


def dispose_engine():
    """Close all connections (call on shutdown)"""
    global _engine
    if _engine:
        _engine.dispose()
        _logger.info("✅ Database connections closed")


def __getattr__(name):
    """
    Lazy attribute access for engine and tables.
    
    Usage:
        from db import engine, user, message
    """
    allowed_names = [
        'engine', 'user', 'user_conversation', 'message', 'conversation',
        'sample_library', 'media_files', 'categories',
    ]
    
    if name in allowed_names:
        engine = get_engine()
        
        if name == 'engine':
            return engine
        else:
            return _tables.get(name)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
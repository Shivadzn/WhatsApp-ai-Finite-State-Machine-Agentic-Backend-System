#!/usr/bin/env python3
"""
Server startup script for WhatsApp AI Backend
Compatible with Windows, Linux, macOS
Supports multiple workers on all platforms with sync DB
"""

import uvicorn
import multiprocessing
import os
import sys
from dotenv import load_dotenv
from config import logger

_logger = logger(__name__)

# Load .env if not in production
if not os.getenv("ENVIRONMENT"):
    load_dotenv()

def main():
    # ✅ Windows multiprocessing support
    if sys.platform == "win64" or sys.platform == "win32":
        multiprocessing.freeze_support()
    
    environment = os.getenv("ENVIRONMENT", "development")
    
    # ✅ Multi-worker support on ALL platforms (thanks to sync DB)
    if environment == "development":
        workers = 1  # Single worker for dev (easier debugging)
    else:
        # Production: Use WORKERS env var or default to CPU count
        workers = int(os.getenv("WORKERS", multiprocessing.cpu_count()))
        _logger.info(f"🖥️  Production mode: {workers} workers on {sys.platform}")

    # Base path
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # SSL configuration
    ssl_keyfile = os.getenv("SSL_KEYFILE")
    ssl_certfile = os.getenv("SSL_CERTFILE")

    # Convert relative paths to absolute
    if ssl_keyfile and not os.path.isabs(ssl_keyfile):
        ssl_keyfile = os.path.join(BASE_DIR, ssl_keyfile)
    if ssl_certfile and not os.path.isabs(ssl_certfile):
        ssl_certfile = os.path.join(BASE_DIR, ssl_certfile)

    # Check SSL files
    use_ssl = (ssl_keyfile and ssl_certfile and 
               os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile))

    # Uvicorn configuration
    config = {
        "app": "app:app",
        "host": "0.0.0.0",
        "port": int(os.getenv("PORT", 5000)),
        "workers": workers,
        "log_level": os.getenv("LOG_LEVEL", "info"),
        "access_log": True,
        "proxy_headers": True,
        "forwarded_allow_ips": "*",
        "loop": "asyncio",
    }

    # SSL (production only)
    if use_ssl and environment == "production":
        config["ssl_keyfile"] = ssl_keyfile
        config["ssl_certfile"] = ssl_certfile
        print("🔒 SSL Enabled")
    else:
        print("⚙️  Running without SSL")

    # Auto-reload (development only)
    if environment == "development":
        config["reload"] = True
        config["reload_delay"] = 2
        config["reload_dirs"] = [".", "blueprints", "utility", "agent_tools"]
        print("🔄 Auto-reload enabled")

    # Status display
    print("=" * 70)
    print(f"🚀 Environment:   {environment}")
    print(f"🖥️  Platform:     {sys.platform}")
    print(f"👥 Workers:      {config['workers']}")
    print(f"🔐 SSL:          {'✅ Enabled' if use_ssl else '❌ Disabled'}")
    print(f"🔄 Auto-reload:  {'✅ Enabled' if config.get('reload') else '❌ Disabled'}")
    print(f"🌐 Port:         {config['port']}")
    print("=" * 70)
    
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n👋 Server shutdown requested")
        _logger.info("Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        _logger.error(f"Server crashed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
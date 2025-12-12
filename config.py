import os
import logging
from dotenv import load_dotenv

load_dotenv()

required_vars = [
    "APP_SECRET_KEY", "GOOGLE_API_KEY", "WHATSAPP_ACCESS_TOKEN",
    "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_GRAPH_URL",
    "BACKEND_BASE_URL", "AI_BACKEND_URL", "VERIFY_TOKEN", "DB_URL", "REDIS_URI"
]

missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_GRAPH_URL = os.getenv("WHATSAPP_GRAPH_URL")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL")
AI_BACKEND_URL = os.getenv("AI_BACKEND_URL")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
DB_URL = os.getenv("DB_URL")
REDIS_URI = os.getenv("REDIS_URI")

# Validate DB_URL format
if DB_URL:
    if not DB_URL.startswith(('postgresql://', 'postgres://')):
        raise ValueError(
            f"❌ Invalid DB_URL format. Must start with 'postgresql://' or 'postgres://'\n"
            f"Current: {DB_URL[:20]}..."
        )
    
    # Extract username for validation
    try:
        auth_part = DB_URL.split('://')[1].split('@')[0]
        username = auth_part.split(':')[0]
        
        # Mask password for logging
        host_part = DB_URL.split('@')[1]
        masked_url = f"postgresql://{username}:****@{host_part}"
        
        print(f"✅ DB_URL configured: {masked_url}")
        print(f"   Username: {username}")
        
        # Warn if username looks suspicious
        if username == "postgresql":
            print("⚠️  WARNING: Username is 'postgresql' - did you mean 'postgres'?")
        
    except (IndexError, AttributeError) as e:
        raise ValueError(f"❌ Malformed DB_URL: {e}")


def logger(name):
    logging.basicConfig(
        format='%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
        level=logging.DEBUG
    )
    Logger = logging.getLogger(name)
    return Logger
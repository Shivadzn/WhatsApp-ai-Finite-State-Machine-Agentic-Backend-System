"""
Configuration and constants for WhatsApp API client

UPDATES:
1. Added comprehensive error code mappings including Error 131009
2. Kept your existing config imports
3. Added helper functions for error categorization
"""

from config import WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_GRAPH_URL

# API Configuration
BASE_URL = WHATSAPP_GRAPH_URL
API_BASE = WHATSAPP_GRAPH_URL + WHATSAPP_PHONE_NUMBER_ID


# ============================================================================
# ERROR CODE MAPPINGS - Comprehensive WhatsApp Business API Error Codes
# ============================================================================

ERROR_MAPPINGS = {
    # Your Original Mappings
    0: "AuthException. Get a new access token.",
    3: "Failed API method. Check app permissions.",
    10: "Permission denied.",
    190: "Access token expired.",
    368: "Temporarily blocked due to policy violations.",
    
    # Authentication & Authorization
    100: "Invalid parameter - check request format and values",
    80007: "Authentication failed - invalid access token",
    
    # Rate Limiting
    130429: "Rate limit exceeded - too many messages sent in a short time",
    131026: "Message sending temporarily blocked - wait before retrying",
    
    # Message & Parameter Issues
    131009: "Parameter value is not valid (Common for unsupported features like typing indicators - this is usually safe to ignore)",
    131031: "Account has been restricted - contact WhatsApp support",
    131047: "Re-engagement message required - user needs to initiate conversation",
    131051: "Unsupported message type - check message format",
    131052: "Media download failed - check media URL or ID",
    131053: "Media upload failed - check media file and size",
    
    # Template Issues  
    132000: "Template parameter format mismatch - check template variables",
    132001: "Template does not exist - verify template name",
    132005: "Template is paused - reactivate template in Meta Business Manager",
    132007: "Template format character policy violated - review template content",
    132012: "Template parameter not in template - check parameter names",
    132015: "Template is in pending state - wait for approval",
    132016: "Template has been rejected - create new template",
    
    # Phone Number & Business Issues
    133000: "Phone number not registered with WhatsApp Business",
    133004: "Phone number is part of a closed experiment",
    133005: "Recipient phone number not valid - check number format",
    133006: "Cloud API phone number cannot be used for this operation",
    133010: "Two-step verification PIN is required",
    
    # Server Errors
    500: "Internal server error - retry after a short delay",
    503: "Service temporarily unavailable - retry after a short delay",
}


# ============================================================================
# ERROR CATEGORIZATION HELPERS
# ============================================================================

# Critical errors that should stop processing
CRITICAL_ERROR_CODES = {
    0, 10, 80007, 190, 368,     # Auth errors
    131031, 131047, 131051,      # Account/message blocking
    133000, 133005, 133006,      # Phone number issues
}

# Non-critical errors that can be safely ignored
IGNORABLE_ERROR_CODES = {
    131009,  # Parameter not valid (typing indicators, etc.)
}

# Errors that should be retried
RETRIABLE_ERROR_CODES = {
    130429, 131026,  # Rate limiting
    500, 503,        # Server errors
}


def is_critical_error(error_code: int) -> bool:
    """Check if error code represents a critical failure"""
    return error_code in CRITICAL_ERROR_CODES


def is_ignorable_error(error_code: int) -> bool:
    """Check if error code can be safely ignored"""
    return error_code in IGNORABLE_ERROR_CODES


def is_retriable_error(error_code: int) -> bool:
    """Check if operation should be retried for this error"""
    return error_code in RETRIABLE_ERROR_CODES


# ============================================================================
# HEADER FUNCTIONS
# ============================================================================

def get_headers():
    """Returns the authorization headers for API requests"""
    return {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }


def get_auth_header():
    """Returns only the authorization header (for file uploads)"""
    return {"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}


# ============================================================================
# MESSAGE TYPE CONSTANTS
# ============================================================================

MESSAGE_TYPES = {
    "TEXT": "text",
    "IMAGE": "image", 
    "VIDEO": "video",
    "AUDIO": "audio",
    "DOCUMENT": "document",
    "LOCATION": "location",
    "TEMPLATE": "template",
    "INTERACTIVE": "interactive",
}


# ============================================================================
# SUPPORTED MEDIA TYPES
# ============================================================================

SUPPORTED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
}

SUPPORTED_VIDEO_TYPES = {
    "video/mp4",
    "video/3gpp",
}

SUPPORTED_AUDIO_TYPES = {
    "audio/aac",
    "audio/mp4",
    "audio/mpeg",
    "audio/amr",
    "audio/ogg",
}

SUPPORTED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/vnd.ms-powerpoint",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
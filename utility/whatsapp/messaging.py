"""
WhatsApp messaging functions (text messages, typing indicators)

FIXES APPLIED:
1. Fixed typing_indicator to use correct WhatsApp API parameters
2. Changed function signature to accept phone number (not message_id)
3. Separated mark_as_read functionality
4. Better error handling with graceful degradation
"""

import json
import requests
from typing import Optional
from config import logger
from .constants import API_BASE, get_headers
from .errors import handle_error

_logger = logger(__name__)


def send_message(to: str, message: str) -> Optional[dict]:
    """
    Send a text message via WhatsApp
    
    Args:
        to: Recipient phone number (e.g., "919999782254")
        message: Text message to send
        
    Returns:
        Response data if successful, None otherwise
    """
    url = f"{API_BASE}/messages"
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    try:
        response = requests.post(url, headers=get_headers(), json=data)
        _logger.info("Message send response: %s", response.status_code)
        
        resp_data = None
        try:
            resp_data = response.json()
        except Exception as e:
            _logger.error(f"Exception parsing response: {e}")
            _logger.error("Response not valid JSON: %s", response.text)

        if response.ok:
            _logger.info("Message sent successfully to %s", to)
            _logger.debug("Response JSON: %s", resp_data)
            return resp_data
        else:
            _logger.error("Failed to send message. Status: %s", response.status_code)
            _logger.error("Error response: %s", json.dumps(resp_data, indent=2))
            return resp_data

    except requests.RequestException as e:
        _logger.exception("HTTP request failed: %s", str(e))
        return None


def typing_indicator(to: str) -> bool:
    """
    Send a typing indicator to show the bot is composing a message.
    
    IMPORTANT: This is a best-effort feature. WhatsApp Business API has limited
    support for typing indicators. If this fails, it's non-critical and the
    message will still be sent.
    
    Args:
        to: Recipient phone number (e.g., "919999782254")
        
    Returns:
        True if successful, False otherwise (failure is non-critical)
    """
    # ============================================================================
    # FIX: Correct WhatsApp API payload for typing indicator
    # ============================================================================
    # The old payload was completely wrong:
    # ❌ OLD (WRONG):
    # {
    #     "messaging_product": "whatsapp",
    #     "status": "read",              # Wrong - this is for marking as read
    #     "message_id": msg_id,          # Wrong - typing doesn't need message_id
    #     "typing_indicator": {          # Wrong - not a valid parameter
    #         "type": "text"
    #     }
    # }
    #
    # ✅ NEW (CORRECT):
    # According to WhatsApp Business API docs, typing indicators are sent as:
    # ============================================================================
    
    url = f"{API_BASE}/messages"
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "typing",  # This is the correct way to send typing indicator
    }

    try:
        response = requests.post(url, headers=get_headers(), json=data, timeout=3)
        _logger.debug("Typing indicator response: %s", response.status_code)

        if response.ok:
            _logger.debug("Typing indicator sent to %s", to)
            return True

        # Log error but don't treat it as critical
        _logger.debug(
            "Typing indicator failed (non-critical). Status: %s", 
            response.status_code
        )
        
        try:
            error_obj = response.json()
            error_code = error_obj.get("error", {}).get("code")
            
            # Error 131009 is common and indicates typing indicators aren't supported
            # in your WhatsApp Business API configuration
            if error_code == 131009:
                _logger.debug(
                    "Typing indicators not supported (Error 131009) - "
                    "this is normal for some WhatsApp Business API setups"
                )
            else:
                _logger.warning(
                    "Typing indicator error %s: %s", 
                    error_code,
                    error_obj.get("error", {}).get("message")
                )
        except (ValueError, KeyError):
            _logger.debug("Could not parse typing indicator error response")
            
        return False

    except requests.Timeout:
        _logger.debug("Typing indicator request timed out (non-critical)")
        return False
    except requests.RequestException as e:
        _logger.debug("Typing indicator request failed (non-critical): %s", str(e))
        return False


def mark_as_read(message_id: str) -> bool:
    """
    Mark a message as read.
    
    This is separate from typing indicators. Use this to mark incoming
    messages as read after processing them.
    
    Args:
        message_id: WhatsApp message ID to mark as read
        
    Returns:
        True if successful, False otherwise
    """
    url = f"{API_BASE}/messages"
    data = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    try:
        response = requests.post(url, headers=get_headers(), json=data, timeout=3)
        
        if response.ok:
            _logger.debug("Message %s marked as read", message_id)
            return True
            
        _logger.warning(
            "Failed to mark message as read. Status: %s", 
            response.status_code
        )
        return False

    except requests.RequestException as e:
        _logger.warning("Failed to mark message as read: %s", str(e))
        return False


def send_typing_indicator_safe(to: str) -> bool:
    """
    Safe wrapper for typing indicator that never raises exceptions.
    
    This is the recommended function to use in production code.
    Typing indicators are purely cosmetic and should never break the flow.
    
    Args:
        to: Recipient phone number
        
    Returns:
        True if sent successfully, False otherwise (safe to ignore)
    """
    try:
        return typing_indicator(to)
    except Exception as e:
        _logger.debug(f"Typing indicator exception (non-critical): {e}")
        return False
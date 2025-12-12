"""
Error handling utilities for WhatsApp API

FIXES APPLIED:
1. Added Error 131009 handling (typing indicator not supported)
2. Better error categorization (critical vs non-critical)
3. Clearer error messages
"""

from typing import Dict
from config import logger
from .constants import ERROR_MAPPINGS

_logger = logger(__name__)


def handle_error(error_obj: Dict, context: str = "") -> None:
    """
    Handles and logs WhatsApp API errors with appropriate severity levels.
    
    Args:
        error_obj: Error response object from API
        context: Optional context string (e.g., "typing_indicator", "send_message")
    """
    error = error_obj.get("error", {})
    error_code = error.get("code")
    error_message = error.get("message", "Unknown error")
    
    # Get error description from mappings
    mapped_message = ERROR_MAPPINGS.get(
        error_code, 
        f"Unknown error code: {error_code}"
    )
    
    # Context prefix for clearer logs
    context_prefix = f"[{context}] " if context else ""
    
    # Categorize errors by severity
    if error_code in [131009]:
        # Non-critical errors (typing indicators not supported, etc.)
        _logger.debug(
            f"{context_prefix}Non-critical error {error_code}: {mapped_message}"
        )
    elif error_code in [100, 80007, 131031, 131047, 131051]:
        # Authentication/permission errors (critical)
        _logger.error(
            f"{context_prefix}CRITICAL Error {error_code}: {mapped_message} - {error_message}"
        )
    elif error_code in [130429, 131026]:
        # Rate limiting (warning)
        _logger.warning(
            f"{context_prefix}Rate limit error {error_code}: {mapped_message}"
        )
    else:
        # Other errors (error level)
        _logger.error(
            f"{context_prefix}Error {error_code}: {mapped_message} - {error_message}"
        )


def is_critical_error(error_code: int) -> bool:
    """
    Determine if an error code represents a critical failure.
    
    Args:
        error_code: WhatsApp API error code
        
    Returns:
        True if error is critical and should stop processing
    """
    critical_codes = {
        100,    # Invalid parameter
        80007,  # Authentication failed
        131031, # Account restricted
        131047, # Message sending blocked
        131051, # Unsupported message type
    }
    return error_code in critical_codes


def is_retriable_error(error_code: int) -> bool:
    """
    Determine if an error can be retried.
    
    Args:
        error_code: WhatsApp API error code
        
    Returns:
        True if operation should be retried
    """
    retriable_codes = {
        130429, # Rate limit exceeded
        131026, # Temporarily blocked
        500,    # Internal server error
        503,    # Service unavailable
    }
    return error_code in retriable_codes


def should_ignore_error(error_code: int) -> bool:
    """
    Determine if an error can be safely ignored.
    
    Args:
        error_code: WhatsApp API error code
        
    Returns:
        True if error is non-critical and can be ignored
    """
    ignorable_codes = {
        131009, # Parameter value is not valid (for typing indicators)
    }
    return error_code in ignorable_codes
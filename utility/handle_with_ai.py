"""
AI Message Handler

Processes user messages with AI, handles responses, and manages database operations.

FIXES APPLIED:
1. Simplified response extraction - AI returns clean strings
2. Better user/AI message separation
3. Proper empty response handling (for intervention)
4. Removed unnecessary typing indicator delay
5. Fixed context handling to prevent message merging
"""

from config import logger
from db import engine, message
from sqlalchemy import insert, select
from datetime import datetime
from bot import stream_graph_updates
from .whatsapp import send_message, typing_indicator, download_media
import json
import time
from typing import Any, Optional, Dict

_logger = logger(__name__)

# ============================================================================
# RESPONSE EXTRACTION (SIMPLIFIED)
# ============================================================================

def _extract_final_text(ai_response: Dict[str, Any]) -> Optional[str]:
    """
    Extract clean text from AI response.
    
    The AI (LangGraph) should return: {"content": "text string", "metadata": {...}}
    
    Args:
        ai_response: Full AI response dict with 'content' and 'metadata'
        
    Returns:
        Clean text string or None if empty (intervention case)
    """
    content = ai_response.get("content", "")
    
    # Handle empty content (intervention scenarios)
    if not content or content == "":
        _logger.info("AI returned empty content (likely intervention requested)")
        return None
    
    # Content should be a clean string from the AI
    if isinstance(content, str):
        cleaned = content.strip()
        
        # Additional validation: ensure it's not just whitespace
        if not cleaned:
            _logger.warning("AI returned whitespace-only content")
            return None
        
        # Additional validation: ensure it's not a stringified dict/list
        if cleaned.startswith('{') or cleaned.startswith('['):
            _logger.warning(f"AI returned structured data as string: {cleaned[:100]}")
            # Try to extract text from it
            try:
                import json
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and 'text' in parsed:
                    return parsed['text'].strip()
                elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                    if 'text' in parsed[0]:
                        return parsed[0]['text'].strip()
            except:
                pass
            
            # If we can't parse it, return as-is and log warning
            _logger.error("Could not extract clean text from structured response")
            return None
        
        return cleaned
    
    # Unexpected type
    _logger.error(
        f"AI returned unexpected content type: {type(content)}. "
        f"Expected string, got: {str(content)[:200]}"
    )
    return None


# ============================================================================
# TYPING INDICATOR (NON-BLOCKING)
# ============================================================================

def _send_typing_indicator_safe(phone_number: str) -> bool:
    """
    Send typing indicator with error handling.
    Non-critical - failure won't stop message flow.
    """
    try:
        typing_indicator(phone_number)
        return True
    except Exception as e:
        error_msg = str(e)
        # Error 131009 is common with typing indicator
        if "131009" in error_msg or "100" in error_msg:
            _logger.debug(f"Typing indicator failed (common WhatsApp API limitation)")
        else:
            _logger.warning(f"Typing indicator error: {e}")
        return False


# ============================================================================
# MAIN AI HANDLER
# ============================================================================

def handle_with_ai(clean_data: dict, conversation_id: int):
    """
    Process user message with AI and send response.
    
    Flow:
    1. Build user input (text/media/context)
    2. Call AI (LangGraph)
    3. Extract response text
    4. Send to WhatsApp
    5. Store in database
    
    Args:
        clean_data: Normalized webhook data
        conversation_id: Database conversation ID
    """
    start_time = time.time()
    user_phone = clean_data["from"]["phone"]
    
    try:
        # 1. Build user input structure
        user_input = user_input_builder(clean_data)
        
        _logger.info(f"📝 Processing message for {user_phone}: {user_input.get('class', 'unknown')}")
        
        # 2. Call AI processing
        ai_response = stream_graph_updates(user_phone, user_input)
        
        # 3. Extract clean text from response
        ai_message = _extract_final_text(ai_response)
        ai_metadata = ai_response.get("metadata")
        
        # 4. Handle empty responses (intervention scenarios)
        if ai_message is None:
            _logger.info(f"✋ No AI message to send for {user_phone} (intervention or empty response)")
            # Don't send anything - operator will take over
            return
        
        # 5. Send typing indicator (optional, non-blocking)
        _send_typing_indicator_safe(user_phone)
        
        # 6. Send message to WhatsApp
        try:
            response = send_message(user_phone, ai_message)
            message_id = response.get("messages", [{}])[0].get("id")
            
            if not message_id:
                _logger.error(f"❌ No message ID in WhatsApp response: {response}")
                return
            
            _logger.info(f"✅ Message sent to {user_phone}: {len(ai_message)} chars")
                
        except Exception as e:
            _logger.error(f"❌ Failed to send message to {user_phone}: {e}", exc_info=True)
            return
        
        # 7. Store AI response in database
        try:
            with engine.begin() as conn:
                row = {
                    "conversation_id": conversation_id,
                    "direction": "outbound",
                    "sender_type": "ai",
                    "external_id": message_id,
                    "has_text": True,
                    "message_text": ai_message,
                    "provider_ts": datetime.fromtimestamp(int(time.time())),
                    "extra_metadata": ai_metadata
                }
                
                conn.execute(insert(message).values(row))
                _logger.debug(f"💾 Stored AI message in DB: {message_id}")
                
        except Exception as e:
            _logger.error(f"❌ Failed to store AI message in DB: {e}", exc_info=True)
            # Continue - message was sent successfully
        
        # 8. Log performance
        total_time = time.time() - start_time
        _logger.info(f"⏱️ Total processing time: {total_time:.2f}s")
        
        if total_time > 10:
            _logger.warning(f"🐌 SLOW: Processing took {total_time:.2f}s for {user_phone}")
            
    except Exception as e:
        _logger.error(
            f"❌ Unhandled error in handle_with_ai for {user_phone}: {e}",
            exc_info=True
        )


# ============================================================================
# USER INPUT BUILDER
# ============================================================================

def user_input_builder(clean_data: dict) -> dict:
    """
    Build structured input for AI from normalized webhook data.
    
    Returns a clean, simple structure that the AI can process:
    - Text: {"class": "text", "message": "user text"}
    - Media: {"class": "media", "category": "image", "data": base64, ...}
    - Context: {"class": "text", "message": "user text", "context": {...}}
    """
    message_class = clean_data.get("class", "text")
    
    # Parse timestamp once
    timestamp = _parse_timestamp(clean_data.get("timestamp"))
    
    # Route to appropriate builder
    if message_class == "text":
        return _build_text_input(clean_data, timestamp)
    elif message_class == "media":
        return _build_media_input(clean_data, timestamp)
    else:
        _logger.warning(f"⚠️ Unknown message class: {message_class}")
        return {
            "class": "text",
            "message": f"[Unsupported message type: {message_class}]"
        }


def _parse_timestamp(timestamp_value: Any) -> Optional[datetime]:
    """Parse Unix timestamp to datetime."""
    if not timestamp_value:
        return None
    
    try:
        return datetime.fromtimestamp(int(timestamp_value))
    except (ValueError, TypeError) as e:
        _logger.warning(f"⚠️ Invalid timestamp {timestamp_value}: {e}")
        return None


def _build_text_input(clean_data: dict, timestamp: Optional[datetime]) -> dict:
    """
    Build input for text messages.
    
    Handles:
    - Simple text
    - Text replying to previous text (context)
    - Text replying to previous media (context)
    """
    user_message = clean_data["from"].get("message", "").strip()
    
    if not user_message:
        _logger.warning("⚠️ Empty text message received")
        return {
            "class": "text",
            "message": "[Empty message]"
        }
    
    # Check for context (reply to previous message)
    context = clean_data.get("context")
    if not context:
        # Simple text message (most common case)
        return {
            "class": "text",
            "message": user_message
        }
    
    # Handle context (user is replying to a previous message)
    context_id = context.get("id")
    if not context_id:
        _logger.warning("⚠️ Context present but no ID")
        return {
            "class": "text",
            "message": user_message
        }
    
    # Fetch the context message from database
    try:
        with engine.begin() as conn:
            result = conn.execute(
                select(
                    message.c.message_text,
                    message.c.media_info,
                    message.c.sender_type,
                    message.c.direction
                ).where(message.c.external_id == context_id)
            )
            context_row = result.mappings().first()
        
        if not context_row:
            _logger.warning(f"⚠️ Context message {context_id} not found in DB")
            return {
                "class": "text",
                "message": user_message
            }
        
        # Build context info
        return {
            "class": "text",
            "message": user_message,
            "context": {
                "type": "media" if context_row["media_info"] else "text",
                "text": context_row["message_text"],
                "sender": context_row["sender_type"],
                "direction": context_row["direction"]
            }
        }
        
    except Exception as e:
        _logger.error(f"❌ Failed to fetch context {context_id}: {e}")
        # Fallback: treat as simple text
        return {
            "class": "text",
            "message": user_message
        }


def _build_media_input(clean_data: dict, timestamp: Optional[datetime]) -> dict:
    """
    Build input for media messages (image, video, audio, document).
    
    Downloads the media and returns base64-encoded data.
    """
    media_id = clean_data["from"].get("media_id")
    category = clean_data.get("category", "file")
    caption = clean_data["from"].get("message", "").strip()
    
    if not media_id:
        _logger.error("❌ Media message missing media_id")
        return {
            "class": "text",
            "message": "[Media processing failed - no ID]"
        }
    
    try:
        # Download media from WhatsApp
        downloaded_data = download_media(media_id, timestamp=timestamp)
        
        if not downloaded_data:
            _logger.error(f"❌ Failed to download media {media_id}")
            return {
                "class": "text",
                "message": "[Media could not be downloaded]"
            }
        
        # Build media input
        media_input = {
            "class": "media",
            "category": category,  # image, video, audio, document
            "data": downloaded_data['data'],  # base64
            "content_type": downloaded_data['content_type'],
            "mime_type": downloaded_data['mime_type']
        }
        
        # Add caption if present
        if caption:
            media_input["message"] = caption
        
        _logger.info(f"📎 Media processed: {category}, {len(downloaded_data['data'])} bytes")
        
        return media_input
        
    except Exception as e:
        _logger.error(f"❌ Error processing media {media_id}: {e}", exc_info=True)
        return {
            "class": "text",
            "message": "[Media processing error]"
        }


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

_logger.info("✅ AI handler module loaded")
"""
LangGraph-based AI Agent with PostgreSQL Persistent Checkpointing

BEST VERSION: Combines Document 6's superior event handling with bug fixes
"""

from typing import Annotated, List
from typing_extensions import TypedDict
import time
import os
import json

# LangGraph and LangChain Imports
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.prebuilt import ToolNode, InjectedState
from langgraph.types import Command
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, InjectedToolCallId
from langchain.chat_models import init_chat_model

# PostgreSQL Checkpointing
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection

# External Dependencies
from config import DB_URL, logger
from agent_tools.media_response_tool import send_media_tool
from agent_tools.request_for_intervention import callIntervention
from utility.content_block import content_formatter

_logger = logger(__name__)  # FIX: Corrected from logger(name_)

# ============================================================================
# POSTGRESQL CHECKPOINTING SETUP
# ============================================================================

_checkpointer = None
_pg_connection = None
_pg_pid = None

def _is_connection_alive(conn) -> bool:
    """Check if PostgreSQL connection is alive"""
    if conn is None:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception as e:
        _logger.warning(f"Connection health check failed: {e}")
        return False


def get_checkpointer():
    """
    Get or create PostgreSQL checkpointer (process-safe).
    
    This function ensures each Celery worker process has its own
    database connection and checkpointer instance.
    
    Returns:
        PostgresSaver: Initialized checkpointer
    """
    global _checkpointer, _pg_connection, _pg_pid
    
    current_pid = os.getpid()
    
    # Check 1: Different process (Celery fork detected)
    if _pg_connection is not None and _pg_pid != current_pid:
        _logger.info(f"Fork detected (PID {_pg_pid} → {current_pid}), recreating connection")
        try:
            _pg_connection.close()
        except:
            pass
        _pg_connection = None
        _checkpointer = None
    
    # Check 2: Dead connection
    elif _pg_connection is not None and not _is_connection_alive(_pg_connection):
        _logger.warning(f"Dead connection detected for PID {current_pid}, recreating...")
        try:
            _pg_connection.close()
        except:
            pass
        _pg_connection = None
        _checkpointer = None
    
    # Create new checkpointer if needed
    if _checkpointer is None:
        _logger.info(f"Creating PostgreSQL checkpointer for PID {current_pid}")
        
        try:
            # FIX: Ensure DB_URL has proper postgresql:// scheme
            db_url = DB_URL
            if not db_url.startswith(('postgresql://', 'postgres://')):
                db_url = f"postgresql://{db_url}"
                _logger.warning(f"Added missing postgresql:// scheme to DB_URL")
            
            # Connect with proper URL
            _pg_connection = Connection.connect(
                db_url,
                autocommit=True,
                prepare_threshold=0,
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
            
            # Test connection
            with _pg_connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            _logger.info("PostgreSQL connection test successful")
            
            # Create checkpointer
            _checkpointer = PostgresSaver(_pg_connection)
            
            # Setup tables (idempotent)
            try:
                _checkpointer.setup()
                _logger.info("PostgreSQL checkpointer tables initialized")
            except Exception as e:
                _logger.debug(f"Checkpointer setup (tables may exist): {e}")
            
            _pg_pid = current_pid
            _logger.info(f"✅ PostgreSQL checkpointer ready for PID {current_pid}")
            
        except Exception as e:
            _logger.error(f"Failed to create checkpointer: {e}", exc_info=True)
            _pg_connection = None
            _checkpointer = None
            raise
    
    return _checkpointer


# ============================================================================
# STATE DEFINITION
# ============================================================================

class State(TypedDict):
    """LangGraph state definition"""
    messages: Annotated[List[AnyMessage], add_messages]
    operator_active: bool
    tool_call_count: int


# ============================================================================
# TOOLS
# ============================================================================

@tool("RespondWithMedia")
def RespondWithMedia(category: str, subcategory: str = "", *, config: RunnableConfig) -> dict:
    """
    Send WhatsApp media from the Joy Invite sample library.

    CATEGORIES WITH SUBCATEGORIES:
    - category="south_india" subcategory in {"2d", "3d", "ai"}
    - category="north_india" subcategory in {"2d", "3d", "ai"}
    - category="punjabi" subcategory in {"2d", "3d"}
    - category="engagement" subcategory in {"2d", "3d"}

    CATEGORIES WITHOUT SUBCATEGORIES:
    - "save_the_date", "welcome_board", "anniversary", "janoi", "muslim",
    - "wardrobe", "story", "house_warming", "baby_shower", "mundan",
    - "birthday", "utility"
    """
    user_ph = config.get("configurable", {}).get("thread_id")
    if not user_ph:
        _logger.error("RespondWithMedia: Missing thread_id")
        return {"status": "error", "message": "Missing user phone number"}

    norm_category = category.strip().lower().replace(" ", "_").replace("-", "_")
    norm_subcat = subcategory.strip().lower()

    CATS_WITH_SUB = {
        "south_india": {"2d", "3d", "ai"},
        "north_india": {"2d", "3d", "ai"},
        "punjabi": {"2d", "3d"},
        "engagement": {"2d", "3d"},
    }

    CATS_NO_SUB = {
        "save_the_date", "welcome_board", "anniversary", "janoi", "muslim",
        "wardrobe", "story", "house_warming", "baby_shower", "mundan",
        "birthday", "utility",
    }

    # Validation
    if norm_category in CATS_WITH_SUB:
        if norm_subcat not in CATS_WITH_SUB[norm_category]:
            return {
                "status": "error",
                "message": f"Invalid subcategory '{subcategory}' for '{category}'. Valid: {sorted(CATS_WITH_SUB[norm_category])}"
            }
    elif norm_category in CATS_NO_SUB:
        if norm_subcat:
            return {"status": "error", "message": f"Category '{category}' does not have subcategories."}
    else:
        return {"status": "error", "message": f"Unknown media category '{category}'."}

    _logger.info(f"[MEDIA TOOL] Calling: category='{norm_category}', subcategory='{norm_subcat}', user_ph={user_ph}")

    try:
        tool_response = send_media_tool(category=norm_category, subcategory=norm_subcat, user_ph=user_ph)
        
        if not tool_response:
            return {"status": "error", "message": "Empty media response"}
            
        _logger.info(f"[MEDIA TOOL] ✅ Success for {user_ph}")
        return {"status": "success", "data": tool_response}
        
    except Exception as e:
        _logger.error(f"[MEDIA TOOL] ❌ Failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


@tool("RequestIntervention")
def RequestIntervention(
    status: bool = True,
    *,
    config: RunnableConfig,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Request manual operator takeover"""
    user_ph = config.get("configurable", {}).get("thread_id")

    if not user_ph:
        _logger.error("RequestIntervention: Missing thread_id")
        return Command(update={
            "messages": [ToolMessage("Error: Missing user phone", tool_call_id=tool_call_id)]
        })

    try:
        callIntervention(state, user_ph)
        _logger.info(f"✋ Intervention requested for {user_ph}")
        
        return Command(update={
            "operator_active": True,
            "messages": [ToolMessage("Intervention requested successfully", tool_call_id=tool_call_id)]
        })
        
    except (ConnectionResetError, ConnectionError, OSError) as e:
        _logger.warning(f"Intervention connection error (non-critical): {e}")
        return Command(update={
            "operator_active": True,
            "messages": [ToolMessage("Intervention requested (connection warning)", tool_call_id=tool_call_id)]
        })
        
    except Exception as e:
        _logger.error(f"Intervention failed: {e}", exc_info=True)
        return Command(update={
            "operator_active": True,
            "messages": [ToolMessage(f"Intervention attempted with error: {str(e)}", tool_call_id=tool_call_id)]
        })


# ============================================================================
# GUARDRAIL
# ============================================================================

def _check_pricing_guardrail(message: str) -> bool:
    """Check if message requires intervention"""
    message_lower = message.lower()
    is_pricing = any(kw in message_lower for kw in ["price", "kitne", "cost", "rate"])
    is_problematic = "birthday" in message_lower or "custom" in message_lower
    
    if is_pricing and is_problematic:
        _logger.warning("🚨 Pricing guardrail triggered")
        return True
    return False


def guardrail_node(state: State) -> Command:
    """Pre-LLM guardrail enforcement"""
    try:
        latest_message = state['messages'][-1].content
    except (IndexError, AttributeError):
        _logger.error("Guardrail: No valid user message")
        return Command(goto=END)

    if state.get('operator_active', False):
        _logger.info("🚫 Operator active, ending")
        return Command(goto=END)

    if _check_pricing_guardrail(latest_message):
        _logger.warning("🚨 Forcing silent intervention")
        ai_message = AIMessage(
            content="",
            tool_calls=[{"name": "RequestIntervention", "args": {"status": True}, "id": "call_intervention_forced"}]
        )
        return Command(update={"messages": [ai_message]}, goto="increment_counter")

    _logger.info("✅ Guardrail passed. Proceeding to Gemini.")
    return Command(goto="gemini")


# ============================================================================
# LLM SETUP
# ============================================================================

# Load system prompt
try:
    with open("gemini_system_prompt.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
    _logger.info("✅ System prompt loaded")
except:
    SYSTEM_PROMPT = "You are a helpful assistant for Joy Invite, a digital invitation service."
    _logger.warning("Using default system prompt")

# Initialize model
gemini = init_chat_model("google_genai:gemini-2.5-flash")
gemini_with_tools = gemini.bind_tools([RespondWithMedia, RequestIntervention])

prompt_template = ChatPromptTemplate.from_messages([
    ("system", "{system_message}"),
    MessagesPlaceholder("messages")
])

gemini_agent = prompt_template | gemini_with_tools


def gemini_node(state: State) -> dict:
    """Main Gemini processing node"""
    try:
        ai_resp = gemini_agent.invoke({
            "system_message": SYSTEM_PROMPT,
            "messages": state['messages']
        })

        has_tools = hasattr(ai_resp, 'tool_calls') and bool(ai_resp.tool_calls)
        content = getattr(ai_resp, 'content', '')
        
        _logger.info(f"🤖 Gemini response: {len(str(content))} chars, tools: {has_tools}")

        # Fix empty content with tool calls
        if has_tools and not str(content).strip():
            tool_names = [tc.get('name') for tc in ai_resp.tool_calls]
            
            if 'RequestIntervention' not in tool_names:
                _logger.error(f"⚠️ CRITICAL: Gemini returned tools WITHOUT content text! Tools: {tool_names}. Adding fallback text.")
                
                first_tool = ai_resp.tool_calls[0]
                args = first_tool.get('args', {})
                subcat = str(args.get('subcategory', '')).lower()
                
                if 'ai' in subcat:
                    ai_resp.content = "Bilkul! AI samples bhej raha hoon 📱"
                elif '3d' in subcat:
                    ai_resp.content = "Haan! 3D samples bhej raha hoon 📱"
                elif '2d' in subcat:
                    ai_resp.content = "Theek hai! 2D samples bhej raha hoon 📱"
                else:
                    ai_resp.content = "Samples bhej raha hoon 📱"
                
                _logger.warning(f"🔧 FIXED: Added fallback text: '{ai_resp.content}'")

        return {"messages": [ai_resp]}
        
    except Exception as e:
        _logger.error(f"❌ Gemini error: {e}", exc_info=True)
        return {"messages": [AIMessage(content="Sorry, kuch technical issue aa gaya. Ek baar phir try kijiye?")]}


def increment_counter_node(state: State) -> dict:
    """Increment tool call counter"""
    current = state.get('tool_call_count', 0)
    new_count = current + 1
    _logger.debug(f"📊 Tool calls: {current} → {new_count}")
    return {"tool_call_count": new_count}


def route_after_gemini(state: State) -> str:
    """Route based on tool calls"""
    MAX_TOOL_CALLS = 2
    
    if state.get('operator_active', False):
        _logger.info("🚫 Operator active")
        return "no_tool_call"

    last_message = state['messages'][-1]
    tool_count = state.get('tool_call_count', 0)

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_names = [tc['name'] for tc in last_message.tool_calls]
        
        if tool_count >= MAX_TOOL_CALLS:
            _logger.warning(f"⚠️ Tool limit ({MAX_TOOL_CALLS}) reached: {tool_names}")
            return "no_tool_call"
            
        _logger.info(f"🔧 Tool calls detected (count: {tool_count + 1}): {tool_names}")
        return "tool_call"
        
    return "no_tool_call"


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node("guardrail_node", guardrail_node)
graph_builder.add_node("gemini", gemini_node)
graph_builder.add_node("tools", ToolNode([RespondWithMedia, RequestIntervention]))
graph_builder.add_node("increment_counter", increment_counter_node)

# Add edges
graph_builder.add_edge(START, "guardrail_node")

graph_builder.add_conditional_edges(
    "guardrail_node",
    lambda state: END if state.get('operator_active', False) else "gemini",
    {"gemini": "gemini", END: END}
)

graph_builder.add_conditional_edges(
    "gemini",
    route_after_gemini,
    {"tool_call": "increment_counter", "no_tool_call": END}
)

graph_builder.add_edge("increment_counter", "tools")
graph_builder.add_edge("tools", "gemini")

_logger.info("✅ Graph built successfully")


def get_graph():
    """Get compiled graph with PostgreSQL checkpointer"""
    try:
        checkpointer = get_checkpointer()
        return graph_builder.compile(
            checkpointer=checkpointer,
            interrupt_before=[],
            interrupt_after=[],
        )
    except Exception as e:
        _logger.error(f"❌ Failed to compile graph: {e}", exc_info=True)
        raise


# ============================================================================
# MAIN EXECUTION (IMPROVED - Node-based streaming)
# ============================================================================

def stream_graph_updates(user_ph: str, user_input: dict) -> dict:
    """
    Process user input and return AI response.
    
    FIXED: Handles None values in updates stream mode
    """
    final_response = {"content": "", "metadata": None}
    config = {"configurable": {"thread_id": user_ph}}
    
    turn_count = 0
    has_content = False
    max_turns = 10
    fallback = "Sorry, kuch technical issue aa gaya. Ek baar phir try kijiye?"
    
    try:
        # Format content
        start_time = time.time()
        content = content_formatter(user_input)
        format_time = time.time() - start_time
        _logger.info(f"📝 Content formatted in {format_time:.2f}s for {user_ph}")
        
        # Get graph
        graph = get_graph()
        
        # Initialize state
        input_state = {
            "messages": [HumanMessage(content=content)],
            "tool_call_count": 0,
            "operator_active": False
        }
        
        # Stream execution
        process_start = time.time()
        
        for events in graph.stream(input_state, config=config, stream_mode="updates"):
            turn_count += 1
            
            if turn_count > max_turns:
                _logger.error(f"⚠️ Max turns ({max_turns}) exceeded")
                if not has_content:
                    final_response["content"] = fallback
                break
            
            # CRITICAL: Check if events is valid
            if not events or not isinstance(events, dict):
                _logger.warning(f"Invalid events structure: {type(events)}")
                continue
            
            # Process each node's updates
            for node_name, values in events.items():
                # CRITICAL: Skip if values is None
                if values is None:
                    _logger.debug(f"NODE: {node_name} returned None (skipping)")
                    continue
                
                # Ensure values is a dict
                if not isinstance(values, dict):
                    _logger.warning(f"NODE: {node_name} returned non-dict: {type(values)}")
                    continue
                
                _logger.debug(f"NODE: {node_name}, keys: {list(values.keys())}")
                
                # ============================================================
                # HANDLE GEMINI NODE
                # ============================================================
                if node_name == "gemini":
                    messages = values.get("messages")
                    if not messages:
                        continue
                    
                    last_message = messages[-1] if isinstance(messages, list) else messages
                    
                    # Extract content
                    content_value = getattr(last_message, 'content', None)
                    if content_value:
                        # Handle list-based content (Gemini 2.0+)
                        if isinstance(content_value, list):
                            for item in content_value:
                                if isinstance(item, dict) and 'text' in item:
                                    text = item['text'].strip()
                                    if text:
                                        final_response['content'] = text
                                        has_content = True
                                        _logger.debug(f"Extracted text from list: {len(text)} chars")
                                        break
                        # Handle string content
                        elif isinstance(content_value, str):
                            text = content_value.strip()
                            if text:
                                final_response['content'] = text
                                has_content = True
                                _logger.debug(f"Extracted text from string: {len(text)} chars")
                    
                    # Extract metadata
                    usage_meta = getattr(last_message, 'usage_metadata', None)
                    if usage_meta and isinstance(usage_meta, dict):
                        final_response["metadata"] = usage_meta
                
                # ============================================================
                # HANDLE TOOLS NODE
                # ============================================================
                elif node_name == "tools":
                    messages = values.get("messages")
                    if not messages:
                        continue
                    
                    tool_message = messages[0] if isinstance(messages, list) else messages
                    tool_name = getattr(tool_message, 'name', None)
                    
                    if tool_name == 'RequestIntervention':
                        _logger.info(f"✋ Intervention executed for {user_ph}")
                        final_response['content'] = ''
                        has_content = True
                    elif tool_name == 'RespondWithMedia':
                        _logger.info(f"📎 Media sent to {user_ph}")
                        # Don't overwrite if we already have content from Gemini
                        if not has_content:
                            final_response['content'] = ''
                            has_content = True
                
                # ============================================================
                # CHECK OPERATOR ACTIVATION
                # ============================================================
                if values.get("operator_active", False):
                    _logger.info(f"✋ Operator activated for {user_ph}")
                    final_response['content'] = ''
                    has_content = True
                    break
        
        process_time = time.time() - process_start
        total_time = time.time() - start_time
        
        _logger.info(
            f"✅ AI complete for {user_ph}: "
            f"{process_time:.2f}s ({turn_count} turns), "
            f"Total: {total_time:.2f}s, Content: {has_content}"
        )
        
        # Fallback if no content after all turns
        if not has_content:
            _logger.warning(f"⚠️ Empty response after {turn_count} turns")
            final_response["content"] = "Main aapki baat samajh nahi paya. Kya aap thoda aur detail mein bata sakte hain?"
            
    except Exception as e:
        _logger.error(f"❌ Graph error for {user_ph}: {e}", exc_info=True)
        final_response = {"content": fallback, "metadata": None}
    
    _logger.info(f"📤 Final: {len(final_response['content'])} chars, {turn_count} turns")
    return final_response
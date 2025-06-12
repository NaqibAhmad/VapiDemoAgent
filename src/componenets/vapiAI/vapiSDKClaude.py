import os
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from src.componenets.claude4o.claude4o_agent import Claude4oAgent
from src.utils.dataclass import CallSession, CallStatus
from vapi import AsyncVapi

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VapiWebSocketAgentClaude:
    """Vapi WebSocket agent using Claude 4o for text completions (text-only, no audio)."""
    def __init__(self, assistant_id: str):
        self.assistant_id = assistant_id
        self.claude = Claude4oAgent()
        self.vapi = AsyncVapi(token=os.environ.get("VAPI_API_KEY"))
        self.on_call_started: Optional[Callable[[str], None]] = None
        self.on_call_ended: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str, Exception], None]] = None
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def handle_text_message(self, call_id: str, messages: list) -> Optional[str]:
        """Handle a text message from Vapi, send to Claude 4o, and return the response."""
        try:
            logger.info(f"Received text message for call {call_id}: {messages}")
            response = await self.claude.get_completion(messages)
            logger.info(f"Claude 4o response for call {call_id}: {response}")
            return response
        except Exception as e:
            logger.error(f"Error handling text message for call {call_id}: {e}")
            if self.on_error:
                self.on_error(call_id, e)
            return None

    # async def start_call(self, call_id: str):
    #     logger.info(f"Call started: {call_id}")
    #     self.active_sessions[call_id] = {"status": "active"}
    #     if self.on_call_started:
    #         self.on_call_started(call_id)

    async def start_call(self, customer_phone: Optional[str] = None) -> Optional[str]:
        """Start a new WebSocket call with the configured assistant."""
        try:
            # Prepare call request
            call_request = {
                "assistant_id": self.assistant_id,
                "transport": {
                    "provider": "vapi.websocket",
                    # "audio": {
                    #     "encoding": self.audio_config.encoding,
                    #     "sample_rate": self.audio_config.sample_rate,
                    #     "container": self.audio_config.container
                    # }
                }
            }
            
            # Add customer phone if provided
            # if customer_phone:
            #     call_request["customer"] = {"number": customer_phone}
            
            # Create the call
            logger.info("Creating WebSocket call...")
            call_response = await self.vapi.calls.create(**call_request)
            print("call RESPONSE: ", call_response)
            
            if not hasattr(call_response, 'id') or not hasattr(call_response, 'transport'):
                logger.error("Invalid call response format")
                return None
            
            call_id = call_response.id
            transport_data = call_response.transport
            if isinstance(transport_data, dict):
                websocket_url = transport_data.get('websocketCallUrl')
            else:
                # If transport is a string or other format, parse it
                import json
                try:
                    transport_dict = json.loads(str(transport_data)) if isinstance(transport_data, str) else transport_data.__dict__
                    websocket_url = transport_dict.get('websocketCallUrl')
                except:
                    logger.error(f"Could not parse transport data: {transport_data}")
                    return None
            
            if not websocket_url:
                logger.error("WebSocket URL not found in transport data")
                return None
            
            logger.info(f"Call created: {call_id}")
            logger.info(f"WebSocket URL: {websocket_url}")
            
            # Create call session
        #     session = CallSession(
        #         call_id=call_id,
        #         websocket_url=websocket_url,
        #         status=CallStatus.INITIALIZING,
        #         audio_input_queue=asyncio.Queue(maxsize=1000),
        #         audio_output_queue=asyncio.Queue(maxsize=1000)
        #     )
            
        #     self.active_sessions[call_id] = session
            
        #     # Start handling the call
        #     asyncio.create_task(self._handle_call_session(session))
            
        #     return call_id
            
        except Exception as e:
            logger.error(f"Error starting call: {e}")
            if self.on_error:
                self.on_error("start_call", e)
            return None


    async def end_call(self, call_id: str):
        logger.info(f"Call ended: {call_id}")
        if call_id in self.active_sessions:
            del self.active_sessions[call_id]
        if self.on_call_ended:
            self.on_call_ended(call_id)

    async def get_active_calls(self) -> Dict[str, str]:
        return {call_id: session["status"] for call_id, session in self.active_sessions.items()}

    async def shutdown(self):
        logger.info("Shutting down VapiWebSocketAgentClaude...")
        self.active_sessions.clear()
        logger.info("Shutdown complete.") 
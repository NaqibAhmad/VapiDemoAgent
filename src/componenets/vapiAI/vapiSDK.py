import os
import asyncio
import json
import logging
import websockets
import wave
import struct
from typing import Optional, Dict, Any, Callable, AsyncGenerator
from vapi import AsyncVapi
from src.componenets.geminiLive.geminiLiveAgent import GeminiClient
from src.utils.dataclass import CallStatus, CallSession, AudioConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VapiWebSocketAgent:
    """Production-ready Vapi WebSocket agent with Gemini integration."""
    
    def __init__(self, assistant_id: str):
        """Initialize the agent with required credentials and configuration."""
        # Validate environment variables
        self.vapi_token = "c0c202b9-8f50-4956-b90e-02d48090d5bf"
        self.gemini_api_key = "AIzaSyCoIFX3XhR18Glr1Xj0NhsXMZxpddwDx7E"
        
        if not self.vapi_token:
            raise ValueError("VAPI_API_KEY environment variable is required")
        if not self.gemini_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        self.assistant_id = assistant_id
        self.vapi = AsyncVapi(token=self.vapi_token)
        self.gemini = GeminiClient(api_key=self.gemini_api_key)
        
        # Configuration
        self.audio_config = AudioConfig()
        self.active_sessions: Dict[str, CallSession] = {}
        self.max_concurrent_calls = 10
        self.heartbeat_interval = 30  # seconds
        self.reconnect_attempts = 3
        self.reconnect_delay = 5  # seconds
        
        # Callbacks
        self.on_call_started: Optional[Callable[[str], None]] = None
        self.on_call_ended: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[str, Exception], None]] = None

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
            session = CallSession(
                call_id=call_id,
                websocket_url=websocket_url,
                status=CallStatus.INITIALIZING,
                audio_input_queue=asyncio.Queue(maxsize=1000),
                audio_output_queue=asyncio.Queue(maxsize=1000)
            )
            
            self.active_sessions[call_id] = session
            
            # Start handling the call
            asyncio.create_task(self._handle_call_session(session))
            
            return call_id
            
        except Exception as e:
            logger.error(f"Error starting call: {e}")
            if self.on_error:
                self.on_error("start_call", e)
            return None

    async def _handle_call_session(self, session: CallSession):
        """Handle a complete call session with WebSocket and Gemini integration."""
        call_id = session.call_id
        
        try:
            logger.info(f"Starting call session: {call_id}")
            
            # Connect to WebSocket with retries
            for attempt in range(self.reconnect_attempts):
                try:
                    session.websocket = await websockets.connect(
                        uri=session.websocket_url,
                        ping_interval=self.heartbeat_interval,
                        ping_timeout=10,
                        close_timeout=10
                    )
                    session.status = CallStatus.CONNECTED
                    logger.info(f"WebSocket connected for call: {call_id}")
                    break
                    
                except Exception as e:
                    logger.warning(f"WebSocket connection attempt {attempt + 1} failed: {e}")
                    if attempt < self.reconnect_attempts - 1:
                        await asyncio.sleep(self.reconnect_delay)
                    else:
                        raise
            
            # Start Gemini session
            session.gemini_task = asyncio.create_task(
                self._start_gemini_session(session)
            )
            
            # Start WebSocket handlers
            websocket_send_task = asyncio.create_task(
                self._websocket_send_handler(session)
            )
            websocket_receive_task = asyncio.create_task(
                self._websocket_receive_handler(session)
            )
            
            session.status = CallStatus.ACTIVE
            
            if self.on_call_started:
                self.on_call_started(call_id)
            
            # Wait for tasks to complete
            await asyncio.gather(
                session.gemini_task,
                websocket_send_task,
                websocket_receive_task,
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Error in call session {call_id}: {e}")
            session.status = CallStatus.ERROR
            if self.on_error:
                self.on_error(call_id, e)
                
        finally:
            await self._cleanup_session(session)

    async def _start_gemini_session(self, session: CallSession):
        """Start and manage the Gemini AI session."""
        call_id = session.call_id
        
        try:
            logger.info(f"Starting Gemini session for call: {call_id}")
            
            async def audio_generator() -> AsyncGenerator[bytes, None]:
                """Generate audio chunks for Gemini from the input queue."""
                while session.status in [CallStatus.CONNECTED, CallStatus.ACTIVE]:
                    try:
                        chunk = await asyncio.wait_for(
                            session.audio_input_queue.get(), timeout=1.0
                        )
                        if chunk is None:
                            break
                        yield chunk
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error in audio generator: {e}")
                        break
            
            def on_gemini_audio(audio_data: bytes):
                """Handle audio output from Gemini."""
                try:
                    if session.status == CallStatus.ACTIVE:
                        asyncio.create_task(
                            session.audio_output_queue.put(audio_data)
                        )
                except Exception as e:
                    logger.error(f"Error queuing Gemini audio: {e}")
            
            # Run Gemini session
            await self.gemini.run_session(audio_generator, on_gemini_audio)
            
        except Exception as e:
            logger.error(f"Error in Gemini session for call {call_id}: {e}")
            raise

    async def _websocket_send_handler(self, session: CallSession):
        """Handle sending audio data to Vapi WebSocket."""
        call_id = session.call_id
        
        try:
            while session.status in [CallStatus.CONNECTED, CallStatus.ACTIVE]:
                try:
                    # Get audio from Gemini output queue
                    audio_data = await asyncio.wait_for(
                        session.audio_output_queue.get(), timeout=1.0
                    )
                    
                    if audio_data is None:
                        break
                    
                    # Send binary audio data to WebSocket
                    await session.websocket.send(audio_data)
                    
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"WebSocket connection closed for call: {call_id}")
                    break
                except Exception as e:
                    logger.error(f"Error sending audio for call {call_id}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in WebSocket send handler for call {call_id}: {e}")

    async def _websocket_receive_handler(self, session: CallSession):
        """Handle receiving audio data from Vapi WebSocket."""
        call_id = session.call_id
        
        try:
            async for message in session.websocket:
                try:
                    if isinstance(message, bytes):
                        # Binary audio data
                        await session.audio_input_queue.put(message)
                        
                    elif isinstance(message, str):
                        # JSON control message
                        control_msg = json.loads(message)
                        await self._handle_control_message(session, control_msg)
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON message received for call {call_id}")
                except Exception as e:
                    logger.error(f"Error processing message for call {call_id}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed for call: {call_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket receive handler for call {call_id}: {e}")

    async def _handle_control_message(self, session: CallSession, message: Dict[str, Any]):
        """Handle control messages from Vapi."""
        call_id = session.call_id
        message_type = message.get("type")
        
        logger.debug(f"Control message for call {call_id}: {message_type}")
        
        if message_type == "call-started":
            logger.info(f"Call started: {call_id}")
            
        elif message_type == "call-ended":
            logger.info(f"Call ended: {call_id}")
            session.status = CallStatus.ENDING
            
        elif message_type == "error":
            error_msg = message.get("message", "Unknown error")
            logger.error(f"Call error for {call_id}: {error_msg}")
            session.status = CallStatus.ERROR

    async def end_call(self, call_id: str):
        """Gracefully end a call."""
        if call_id not in self.active_sessions:
            logger.warning(f"Call {call_id} not found in active sessions")
            return
        
        session = self.active_sessions[call_id]
        
        try:
            logger.info(f"Ending call: {call_id}")
            session.status = CallStatus.ENDING
            
            # Send end call message
            if session.websocket and not session.websocket.close_code:
                end_message = json.dumps({"type": "end-call"})
                await session.websocket.send(end_message)
                
            # Signal end to audio queues
            if session.audio_input_queue:
                await session.audio_input_queue.put(None)
            if session.audio_output_queue:
                await session.audio_output_queue.put(None)
                
        except Exception as e:
            logger.error(f"Error ending call {call_id}: {e}")

    async def _cleanup_session(self, session: CallSession):
        """Clean up resources for a call session."""
        call_id = session.call_id
        
        try:
            logger.info(f"Cleaning up session: {call_id}")
            
            # Cancel Gemini task
            if session.gemini_task and not session.gemini_task.done():
                session.gemini_task.cancel()
                try:
                    await session.gemini_task
                except asyncio.CancelledError:
                    pass
            
            # Close WebSocket
            if session.websocket and not session.websocket.close_code:
                await session.websocket.close()
            
            # Update status
            session.status = CallStatus.ENDED
            
            # Remove from active sessions
            if call_id in self.active_sessions:
                del self.active_sessions[call_id]
            
            if self.on_call_ended:
                self.on_call_ended(call_id)
                
        except Exception as e:
            logger.error(f"Error cleaning up session {call_id}: {e}")

    async def get_active_calls(self) -> Dict[str, CallStatus]:
        """Get status of all active calls."""
        return {
            call_id: session.status 
            for call_id, session in self.active_sessions.items()
        }

    async def shutdown(self):
        """Gracefully shutdown the agent."""
        logger.info("Shutting down Vapi WebSocket agent...")
        
        # End all active calls
        call_ids = list(self.active_sessions.keys())
        for call_id in call_ids:
            await self.end_call(call_id)
        
        # Wait for cleanup
        await asyncio.sleep(2)
        
        logger.info("Agent shutdown complete")

# Example usage and configuration

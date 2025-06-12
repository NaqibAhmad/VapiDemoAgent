from dataclasses import dataclass
from enum import Enum
from typing import Optional
import websockets
import asyncio

class CallStatus(Enum):
    INITIALIZING = "initializing"
    CONNECTED = "connected"
    ACTIVE = "active"
    ENDING = "ending"
    ENDED = "ended"
    ERROR = "error"

@dataclass
class AudioConfig:
    """Audio configuration for WebSocket streaming."""
    sample_rate: int = 16000
    channels: int = 1
    bit_depth: int = 16
    encoding: str = "pcm_s16le"
    container: str = "raw"

@dataclass
class CallSession:
    """Represents an active call session."""
    call_id: str
    websocket_url: str
    status: CallStatus
    websocket: Optional[websockets.WebSocketServerProtocol] = None
    gemini_task: Optional[asyncio.Task] = None
    audio_input_queue: Optional[asyncio.Queue] = None
    audio_output_queue: Optional[asyncio.Queue] = None
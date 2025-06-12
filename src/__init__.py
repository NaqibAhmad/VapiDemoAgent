import asyncio
from datetime import datetime, timedelta
import json
import os
from typing import Optional
from fastapi import FastAPI, Request, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from fastapi import WebSocket
from twilio.twiml.voice_response import VoiceResponse, Dial
from vapi import AsyncVapi
import logging
from src.routes import gptRouter
# from src.routes import vapiRouter
# from src.componenets.customLLMs.gpt4o import custom_llm_test


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def hello():
    return {"status": "ok"}

app.include_router(gptRouter.router, prefix="/custom-llm-test", tags=["custom-llm-test"])
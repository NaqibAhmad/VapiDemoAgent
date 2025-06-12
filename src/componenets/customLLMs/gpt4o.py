import os 
import logging
from fastapi import FastAPI, APIRouter, Request, Response
from openai import AsyncOpenAI
from fastapi.responses import StreamingResponse
from anthropic import AsyncAnthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OpenAIgpt4o:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def stream_response(self, data):
        async for message in data:
            json_data = message.model_dump_json()
            print("json_data", json_data)
            yield f"data: {json_data}\n\n"


    async def openai_sse_chat_completions(self, request_data):
        # request_data = await request.json()

        logger.info(f"Request: {request_data}")
        streaming = request_data.get("stream", True)

        prompt = f"""
        your name is DemoProductAgent
        You are a helpful assistant that can answer questions and help with tasks.
        You are given a prompt and you need to answer the question or help with the task.
        """

        messages = [
            {"role": "system", "content": prompt}
        ]

        print("request_data", request_data)
        if streaming:
            chat_completion_stream = await self.client.chat.completions.create(
                model=request_data.get("model"),
                messages=request_data.get("messages") + messages,
                max_tokens=request_data.get("max_tokens"),
                temperature=request_data.get("temperature"),
                stream=True
            )
            return StreamingResponse(self.stream_response(chat_completion_stream), media_type="text/event-stream")
        
        else:
            chat_completion = await self.client.chat.completions.create(**request_data)
            return StreamingResponse(chat_completion.model_dump_json(), media_type="application/json")
    


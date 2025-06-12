from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from src.componenets.customLLMs.gpt4o import OpenAIgpt4o
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = APIRouter()
# claude_agent = Claude4oAgent()
# claude_ws_agent = VapiWebSocketAgentClaude(assistant_id=os.environ.get("VAPI_ASSISTANT_ID"))
gpt4o_agent = OpenAIgpt4o()

@router.post("/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    if not messages:
        return JSONResponse(status_code=400, content={"error": "Missing 'messages' field"})
    try:
        output = await gpt4o_agent.openai_sse_chat_completions(data)
        print("output", output)
        return output
    except Exception as e:
        logger.error(f"gpt4o error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
import os
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
class Claude4oAgent:
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        # self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        # self.client = AsyncAnthropic(api_key=self.api_key)
        self.client = AsyncOpenAI(api_key=self.api_key)

    # async def get_completion(self, messages, max_tokens=1024):
    #     # messages: list of {"role": "user"/"assistant", "content": str}
    #     response = await self.client.messages.create(
    #         model=self.model,
    #         max_tokens=max_tokens,
    #         messages=messages
    #     )
    #     return response.content 
    async def get_completion(self, messages, max_tokens=1024):
        # messages: list of {"role": "user"/"assistant", "content": str}
        response = await self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=messages
        )
        return response.choices[0].message.content
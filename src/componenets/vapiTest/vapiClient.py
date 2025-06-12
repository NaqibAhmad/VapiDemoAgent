from vapi import Vapi, AsyncVapi
from vapi.core.api_error import ApiError
import logging

class VapiClient:
    def __init__(self, token: str):
        self.token = token
        self.client = Vapi(token=token)
        self.async_client = AsyncVapi(token=token)
        self.logger = logging.getLogger("VapiClient")

    def create_call(self, **kwargs):
        try:
            return self.client.calls.create(**kwargs)
        except ApiError as e:
            self.logger.error(f"VAPI API error: {e.status_code} {e.body}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    def get_call(self, call_id: str):
        try:
            return self.client.calls.get(call_id)
        except ApiError as e:
            self.logger.error(f"VAPI API error: {e.status_code} {e.body}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    async def create_call_async(self, **kwargs):
        try:
            return await self.async_client.calls.create(**kwargs)
        except ApiError as e:
            self.logger.error(f"VAPI API error: {e.status_code} {e.body}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    async def get_call_async(self, call_id: str):
        try:
            return await self.async_client.calls.get(call_id)
        except ApiError as e:
            self.logger.error(f"VAPI API error: {e.status_code} {e.body}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise
import asyncio
from google import genai
from google.genai import types

class GeminiClient:
    def __init__(self, api_key:str):
        self.client = genai.Client(api_key=api_key)
        self.model = "models/gemini-2.5-flash-preview-native-audio-dialog"

    async def run_session(self, mic_audio_gen, on_audio_out):
        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction="You are a demo assistant that pitches the product concisely."
        )
        async with self.client.aio.live.connect(model=self.model, config=config) as sess:
            send = asyncio.create_task(self._send(sess, mic_audio_gen))
            recv = asyncio.create_task(self._recv(sess, on_audio_out))
            await asyncio.gather(send, recv)

    async def _send(self, sess, gen):
        async for pcm in gen():
            blob = types.Blob(data=pcm, mime_type="audio/pcm;rate=16000")
            await sess.send_realtime_input(audio=blob)

    async def _recv(self, sess, on_audio_out):
        async for resp in sess.receive():
            if resp.data:
                on_audio_out(resp.data)

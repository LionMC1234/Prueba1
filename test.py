import asyncio

from openai import AsyncOpenAI
from openai.helpers import LocalAudioPlayer

openai = AsyncOpenAI(base_url="https://api.electronhub.top/v1", api_key="ek-wLbc5cHir11yu2y0KajzK3dBfTpnZVpiZ84gMvaptEdxYFKCbT")

async def main() -> None:
    async with openai.audio.speech.with_streaming_response.create(
        model="myshell-tts",
        voice="emma",
        input="Today is a wonderful day to build something people love!",
        instructions="Speak in a cheerful and positive tone.",
        response_format="pcm",
    ) as response:
        await LocalAudioPlayer().play(response)

if __name__ == "__main__":
    asyncio.run(main())
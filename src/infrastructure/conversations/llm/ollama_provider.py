from collections.abc import AsyncIterator

from ollama import AsyncClient


class OllamaLLMProvider:
    def __init__(self, *, url: str, model: str) -> None:
        self._client = AsyncClient(host=url)
        self._model = model

    async def stream(self, *, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        ollama_messages = [{"role": "system", "content": system}, *messages]
        async for part in await self._client.chat(model=self._model, messages=ollama_messages, stream=True):
            content = part["message"]["content"]
            if content:
                yield content

from collections.abc import AsyncIterator
from typing import cast

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam


class AnthropicLLMProvider:
    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def stream(self, *, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        # LLMProvider's Protocol keeps `messages` as plain dicts so every adapter can shape
        # them for its own SDK — mypy can't verify a dict[str, str] against MessageParam's
        # Literal["user", "assistant", "system"] role without this cast, but our own
        # Message.role is always "user"/"assistant" (see domain/conversations/entities.py).
        anthropic_messages = cast(list[MessageParam], messages)
        async with self._client.messages.stream(
            model=self._model, max_tokens=4096, system=system, messages=anthropic_messages
        ) as stream:
            async for text in stream.text_stream:
                yield text

from collections.abc import AsyncIterator
from typing import cast

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam


class AnthropicLLMProvider:
    def __init__(self, *, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def stream(self, *, system: str, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        # Domain message roles match the roles accepted by MessageParam.
        anthropic_messages = cast(list[MessageParam], messages)
        async with self._client.messages.stream(
            model=self._model, max_tokens=4096, system=system, messages=anthropic_messages
        ) as stream:
            async for text in stream.text_stream:
                yield text

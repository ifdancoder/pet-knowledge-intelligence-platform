from unittest.mock import AsyncMock, MagicMock, patch

from infrastructure.conversations.llm.anthropic_provider import AnthropicLLMProvider


async def test_stream_yields_text_deltas_from_the_sdk_s_text_stream() -> None:
    async def fake_text_stream():
        yield "Hel"
        yield "lo"

    fake_stream_context = MagicMock()
    fake_stream_context.__aenter__ = AsyncMock(return_value=MagicMock(text_stream=fake_text_stream()))
    fake_stream_context.__aexit__ = AsyncMock(return_value=False)

    with patch("infrastructure.conversations.llm.anthropic_provider.AsyncAnthropic") as mock_cls:
        mock_client = mock_cls.return_value
        mock_client.messages.stream = MagicMock(return_value=fake_stream_context)

        provider = AnthropicLLMProvider(api_key="sk-test", model="claude-sonnet-5")
        deltas = [
            d async for d in provider.stream(system="be helpful", messages=[{"role": "user", "content": "hi"}])
        ]

        assert deltas == ["Hel", "lo"]
        mock_cls.assert_called_once_with(api_key="sk-test")
        mock_client.messages.stream.assert_called_once_with(
            model="claude-sonnet-5", max_tokens=4096, system="be helpful",
            messages=[{"role": "user", "content": "hi"}],
        )

from unittest.mock import AsyncMock, patch

from infrastructure.conversations.llm.ollama_provider import OllamaLLMProvider


async def test_stream_prepends_a_system_message_and_yields_text_deltas() -> None:
    async def fake_stream():
        yield {"message": {"content": "Hel"}}
        yield {"message": {"content": "lo"}}
        yield {"message": {"content": ""}}  # a trailing empty delta must be skipped

    with patch("infrastructure.conversations.llm.ollama_provider.AsyncClient") as mock_cls:
        mock_client = mock_cls.return_value
        mock_client.chat = AsyncMock(return_value=fake_stream())

        provider = OllamaLLMProvider(url="http://localhost:11434", model="llama3.2:1b")
        deltas = [d async for d in provider.stream(system="be helpful", messages=[{"role": "user", "content": "hi"}])]

        assert deltas == ["Hel", "lo"]
        mock_cls.assert_called_once_with(host="http://localhost:11434")
        mock_client.chat.assert_called_once_with(
            model="llama3.2:1b",
            messages=[{"role": "system", "content": "be helpful"}, {"role": "user", "content": "hi"}],
            stream=True,
        )

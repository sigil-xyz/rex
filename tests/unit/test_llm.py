from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rex.config import LlmConfig
from rex.daemon.llm import respond, respond_streaming


def _config() -> LlmConfig:
    return LlmConfig(model="test-model", api_key="test-key", max_tokens=64)


def _mock_response(content: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_returns_llm_content(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create = AsyncMock(
        return_value=_mock_response("I am Rex.")
    )
    result = await respond("what's your name", _config(), [])
    assert result == "I am Rex."


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_system_prompt_sent(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create = AsyncMock(
        return_value=_mock_response("ok")
    )
    cfg = _config()
    await respond("hello", cfg, [])
    call_kwargs = mock_openai.return_value.chat.completions.create.call_args
    messages = call_kwargs.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == cfg.system_prompt
    assert messages[-1] == {"role": "user", "content": "hello"}


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_empty_content_returns_empty_string(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create = AsyncMock(
        return_value=_mock_response("")
    )
    assert await respond("hi", _config(), []) == ""


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_api_error_returns_fallback(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create = AsyncMock(
        side_effect=Exception("timeout")
    )
    result = await respond("hi", _config(), [])
    assert result == "Sorry, I couldn't process that."


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_client_reused_across_calls(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create = AsyncMock(
        return_value=_mock_response("ok")
    )
    cfg = _config()
    await respond("first", cfg, [])
    await respond("second", cfg, [])
    assert mock_openai.call_count == 1


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_streaming_yields_sentences(mock_openai: MagicMock) -> None:
    async def _fake_stream(*_a: object, **_kw: object) -> MagicMock:
        chunks = ["Hello there. ", "How are ", "you? ", "Fine."]

        async def _aiter(_self: object) -> object:
            for text in chunks:
                chunk = MagicMock()
                chunk.choices[0].delta.content = text
                yield chunk

        stream = MagicMock()
        stream.__aiter__ = _aiter
        return stream

    mock_openai.return_value.chat.completions.create = _fake_stream
    sentences = [s async for s in respond_streaming("hi", _config(), [])]
    assert sentences == ["Hello there.", "How are you?", "Fine."]


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_streaming_error_yields_fallback(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create = AsyncMock(
        side_effect=Exception("network error")
    )
    sentences = [s async for s in respond_streaming("hi", _config(), [])]
    assert sentences == ["Sorry, I couldn't process that."]


@pytest.mark.parametrize(
    "history_roles",
    [
        [],
        [("user", "ping"), ("assistant", "pong")],
    ],
)
@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_history_injected_between_system_and_user(
    mock_openai: MagicMock, history_roles: list[tuple[str, str]]
) -> None:
    mock_openai.return_value.chat.completions.create = AsyncMock(
        return_value=_mock_response("ok")
    )
    history = [{"role": r, "content": c} for r, c in history_roles]
    await respond("new message", _config(), history)  # type: ignore[arg-type]
    messages = mock_openai.return_value.chat.completions.create.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[-1] == {"role": "user", "content": "new message"}
    mid = messages[1:-1]
    assert [(m["role"], m["content"]) for m in mid] == history_roles

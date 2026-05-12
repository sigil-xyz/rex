from unittest.mock import MagicMock, patch

from rex.config import LlmConfig
from rex.daemon.llm import respond


def _config() -> LlmConfig:
    return LlmConfig(model="test-model", api_key="test-key", max_tokens=64)


def _mock_response(content: str) -> MagicMock:
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.OpenAI")
def test_returns_llm_content(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create.return_value = _mock_response("I am Rex.")
    result = respond("what's your name", _config())
    assert result == "I am Rex."


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.OpenAI")
def test_system_prompt_sent(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create.return_value = _mock_response("ok")
    cfg = _config()
    respond("hello", cfg)
    call_kwargs = mock_openai.return_value.chat.completions.create.call_args
    messages = call_kwargs.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == cfg.system_prompt
    assert messages[1] == {"role": "user", "content": "hello"}


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.OpenAI")
def test_empty_content_returns_empty_string(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create.return_value = _mock_response("")
    assert respond("hi", _config()) == ""


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.OpenAI")
def test_api_error_returns_fallback(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create.side_effect = Exception("timeout")
    result = respond("hi", _config())
    assert result == "Sorry, I couldn't process that."


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.OpenAI")
def test_client_reused_across_calls(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create.return_value = _mock_response("ok")
    cfg = _config()
    respond("first", cfg)
    respond("second", cfg)
    assert mock_openai.call_count == 1

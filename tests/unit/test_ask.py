import sys
from unittest.mock import AsyncMock, patch

import pytest

from rex.config import RexConfig


def _config_with_key() -> RexConfig:
    c = RexConfig()
    c.llm.api_key = "test-key"
    c.memory_db = ":memory:"
    return c


def _config_no_key() -> RexConfig:
    c = RexConfig()
    c.llm.api_key = ""
    c.memory_db = ":memory:"
    return c


# --- ask_main ---


def test_ask_main_no_args_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-ask"])
    from rex.cli.ask import ask_main

    with pytest.raises(SystemExit) as exc:
        ask_main()
    assert exc.value.code == 1


def test_ask_main_no_api_key_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-ask", "hello"])
    from rex.cli.ask import ask_main

    with (
        patch("rex.cli.ask.load_config", return_value=_config_no_key()),
        pytest.raises(SystemExit) as exc,
    ):
        ask_main()
    assert exc.value.code == 1


def test_ask_main_calls_run_query(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-ask", "what", "time", "is", "it"])
    from rex.cli.ask import ask_main

    mock_rq = AsyncMock()
    with (
        patch("rex.cli.ask.load_config", return_value=_config_with_key()),
        patch("rex.cli.ask.run_query", mock_rq),
    ):
        ask_main()

    mock_rq.assert_called_once()
    call_args = mock_rq.call_args[0]
    assert call_args[0] == "what time is it"
    assert call_args[3] == "text"


def test_ask_main_multi_word_question(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-ask", "what", "time", "is", "it"])
    from rex.cli.ask import ask_main

    mock_rq = AsyncMock()
    with (
        patch("rex.cli.ask.load_config", return_value=_config_with_key()),
        patch("rex.cli.ask.run_query", mock_rq),
    ):
        ask_main()

    assert mock_rq.call_args[0][0] == "what time is it"


# --- chat_main ---


def test_chat_main_no_api_key_exits_1() -> None:
    from rex.cli.ask import chat_main

    with (
        patch("rex.cli.ask.load_config", return_value=_config_no_key()),
        pytest.raises(SystemExit) as exc,
    ):
        chat_main()
    assert exc.value.code == 1


def test_chat_main_exit_command_terminates() -> None:
    from rex.cli.ask import chat_main

    call_count = 0

    def _fake_input(_prompt: str) -> str:
        nonlocal call_count
        call_count += 1
        return "exit"

    mock_rq = AsyncMock()
    with (
        patch("rex.cli.ask.load_config", return_value=_config_with_key()),
        patch("rex.cli.ask.run_query", mock_rq),
        patch("builtins.input", _fake_input),
    ):
        chat_main()

    mock_rq.assert_not_called()


def test_chat_main_eof_terminates_cleanly() -> None:
    from rex.cli.ask import chat_main

    def _fake_input(_prompt: str) -> str:
        raise EOFError

    mock_rq = AsyncMock()
    with (
        patch("rex.cli.ask.load_config", return_value=_config_with_key()),
        patch("rex.cli.ask.run_query", mock_rq),
        patch("builtins.input", _fake_input),
    ):
        chat_main()

    mock_rq.assert_not_called()


def test_chat_main_calls_run_query_per_turn() -> None:
    from rex.cli.ask import chat_main

    responses = ["hello", EOFError]
    idx = 0

    def _fake_input(_prompt: str) -> str:
        nonlocal idx
        val = responses[idx]
        idx += 1
        if isinstance(val, type) and issubclass(val, Exception):
            raise val
        return val  # type: ignore[return-value]

    mock_rq = AsyncMock()
    with (
        patch("rex.cli.ask.load_config", return_value=_config_with_key()),
        patch("rex.cli.ask.run_query", mock_rq),
        patch("builtins.input", _fake_input),
    ):
        chat_main()

    mock_rq.assert_called_once()
    assert mock_rq.call_args[0][0] == "hello"

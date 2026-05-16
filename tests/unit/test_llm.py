from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rex.config import LlmConfig
from rex.daemon.llm import (
    ToolCallRequest,
    build_messages,
    respond,
    respond_streaming,
    respond_with_tool_result,
)


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
    mock_openai.return_value.chat.completions.create = AsyncMock(return_value=_mock_response("ok"))
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
    mock_openai.return_value.chat.completions.create = AsyncMock(return_value=_mock_response(""))
    assert await respond("hi", _config(), []) == ""


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_api_error_returns_fallback(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create = AsyncMock(side_effect=Exception("timeout"))
    result = await respond("hi", _config(), [])
    assert result == "Sorry, I couldn't process that."


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_client_reused_across_calls(mock_openai: MagicMock) -> None:
    mock_openai.return_value.chat.completions.create = AsyncMock(return_value=_mock_response("ok"))
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
                chunk.choices[0].delta.tool_calls = None
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


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_respond_streaming_yields_tool_call_request(mock_openai: MagicMock) -> None:
    def _tool_chunk(id: str | None, name: str | None, args: str) -> MagicMock:
        tc = MagicMock()
        tc.id = id
        tc.index = 0
        tc.function.name = name
        tc.function.arguments = args
        return tc

    async def _fake_stream(*_a: object, **_kw: object) -> MagicMock:
        chunks = [
            (_tool_chunk("call_abc", "shell", '{"command":'), None),
            (_tool_chunk(None, None, ' "ls"}'), None),
        ]

        async def _aiter(_self: object) -> object:
            for tc, content in chunks:
                chunk = MagicMock()
                chunk.choices[0].delta.content = content
                chunk.choices[0].delta.tool_calls = [tc] if tc is not None else None
                yield chunk

        stream = MagicMock()
        stream.__aiter__ = _aiter
        return stream

    mock_openai.return_value.chat.completions.create = _fake_stream
    items = [s async for s in respond_streaming("run ls", _config(), [])]
    assert len(items) == 1
    assert isinstance(items[0], ToolCallRequest)
    assert items[0].name == "shell"
    assert items[0].args == {"command": "ls"}
    assert items[0].id == "call_abc"


@patch("rex.daemon.llm._client", None)
@patch("rex.daemon.llm.AsyncOpenAI")
async def test_respond_with_tool_result_streams_sentences(mock_openai: MagicMock) -> None:
    async def _fake_stream(*_a: object, **_kw: object) -> MagicMock:
        chunks = ["The file has ", "three lines. ", "All look fine."]

        async def _aiter(_self: object) -> object:
            for text in chunks:
                chunk = MagicMock()
                chunk.choices[0].delta.content = text
                yield chunk

        stream = MagicMock()
        stream.__aiter__ = _aiter
        return stream

    mock_openai.return_value.chat.completions.create = _fake_stream
    tool_call = ToolCallRequest(id="call_xyz", name="read_file", args={"path": "/tmp/f.txt"})
    msgs: list = [{"role": "user", "content": "read that file"}]
    sentences = [
        s async for s in respond_with_tool_result(msgs, tool_call, "line1\nline2\nline3", _config())
    ]
    assert sentences == ["The file has three lines.", "All look fine."]


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
    mock_openai.return_value.chat.completions.create = AsyncMock(return_value=_mock_response("ok"))
    history = [{"role": r, "content": c} for r, c in history_roles]
    await respond("new message", _config(), history)  # type: ignore[arg-type]
    messages = mock_openai.return_value.chat.completions.create.call_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[-1] == {"role": "user", "content": "new message"}
    mid = messages[1:-1]
    assert [(m["role"], m["content"]) for m in mid] == history_roles


# --- build_messages context injection ---


def test_facts_appended_to_system_prompt() -> None:
    cfg = _config()
    msgs = build_messages("hi", cfg, [], facts=["name is Vinod", "uses Arch Linux"])
    system_content = msgs[0]["content"]
    assert "Facts about the user" in system_content  # type: ignore[operator]
    assert "name is Vinod" in system_content  # type: ignore[operator]
    assert "uses Arch Linux" in system_content  # type: ignore[operator]


def test_project_context_appended_to_system_prompt() -> None:
    cfg = _config()
    msgs = build_messages("hi", cfg, [], project_context="A FastAPI project called orbit")
    system_content = msgs[0]["content"]
    assert "Project context" in system_content  # type: ignore[operator]
    assert "FastAPI" in system_content  # type: ignore[operator]


def test_recent_tool_calls_injected_as_separate_system_message() -> None:
    cfg = _config()
    tc = [
        {
            "tool_name": "shell",
            "args": '{"command":"ls"}',
            "result": "file.txt",
            "status": "completed",
        }
    ]
    msgs = build_messages("hi", cfg, [], recent_tool_calls=tc)
    system_msgs = [m for m in msgs if m["role"] == "system"]
    assert len(system_msgs) == 2
    tool_msg_content = system_msgs[1]["content"]
    assert "shell" in tool_msg_content  # type: ignore[operator]


def test_no_context_produces_same_structure() -> None:
    cfg = _config()
    msgs = build_messages("hello", cfg, [])
    assert len(msgs) == 2
    assert msgs[0]["role"] == "system"
    assert msgs[1] == {"role": "user", "content": "hello"}


def test_empty_facts_list_skips_facts_block() -> None:
    cfg = _config()
    msgs = build_messages("hi", cfg, [], facts=[])
    assert "Facts about the user" not in msgs[0]["content"]  # type: ignore[operator]


def test_facts_and_project_context_both_present() -> None:
    cfg = _config()
    msgs = build_messages(
        "hi",
        cfg,
        [],
        facts=["uses neovim"],
        project_context="This is the rex project",
    )
    system_content = msgs[0]["content"]
    assert "Facts about the user" in system_content  # type: ignore[operator]
    assert "Project context" in system_content  # type: ignore[operator]
    assert "uses neovim" in system_content  # type: ignore[operator]
    assert "rex project" in system_content  # type: ignore[operator]

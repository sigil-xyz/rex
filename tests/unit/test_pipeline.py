from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sqlite3

from rex.config import RexConfig
from rex.daemon.llm import ToolCallRequest
from rex.daemon.memory import init_db, save_fact, save_tool_call, save_turn
from rex.daemon.pipeline import (
    _confirmation_prompt,
    _format_tool_result,
    _load_project_context,
    _run_tool_inline,
    confirm_text,
    run_query,
)
from rex.daemon.tools import ToolResult


def _make_config() -> RexConfig:
    c = RexConfig()
    c.memory_db = ":memory:"
    return c


def _make_db() -> object:
    return init_db(":memory:")


# --- _format_tool_result ---


def test_format_tool_result_error_returns_message() -> None:
    tool = ToolCallRequest(id="x", name="read_file", args={})
    result = ToolResult(output="", error="File not found")
    assert "didn't work" in _format_tool_result(tool, result)
    assert "File not found" in _format_tool_result(tool, result)


def test_format_tool_result_write_file_returns_output() -> None:
    tool = ToolCallRequest(id="x", name="write_file", args={})
    result = ToolResult(output="Written 5 bytes")
    assert _format_tool_result(tool, result) == "Written 5 bytes"


def test_format_tool_result_clipboard_write() -> None:
    tool = ToolCallRequest(id="x", name="clipboard_write", args={})
    result = ToolResult(output="Copied.")
    assert _format_tool_result(tool, result) == "Done, copied to clipboard."


def test_format_tool_result_empty_clipboard_read() -> None:
    tool = ToolCallRequest(id="x", name="clipboard_read", args={})
    result = ToolResult(output="")
    assert _format_tool_result(tool, result) == "The clipboard is empty."


def test_format_tool_result_shell_no_output() -> None:
    tool = ToolCallRequest(id="x", name="shell", args={})
    result = ToolResult(output="(no output)")
    assert "no output" in _format_tool_result(tool, result)


def test_format_tool_result_read_file_empty() -> None:
    tool = ToolCallRequest(id="x", name="read_file", args={})
    result = ToolResult(output="")
    assert _format_tool_result(tool, result) == "The file is empty."


def test_format_tool_result_error_with_dep_hint() -> None:
    tool = ToolCallRequest(id="x", name="web_search", args={})
    result = ToolResult(output="", error="ddgr not found — install ddgr")
    formatted = _format_tool_result(tool, result)
    assert "sudo pacman -S ddgr" in formatted


# --- _confirmation_prompt ---


def test_confirmation_prompt_shell() -> None:
    tool = ToolCallRequest(id="x", name="shell", args={"command": "ls"})
    assert _confirmation_prompt(tool) == "Run: ls?"


def test_confirmation_prompt_write_file() -> None:
    tool = ToolCallRequest(id="x", name="write_file", args={"path": "/tmp/x.txt"})
    assert "Write to" in _confirmation_prompt(tool)


def test_confirmation_prompt_generic() -> None:
    tool = ToolCallRequest(id="x", name="read_file", args={})
    assert "read_file" in _confirmation_prompt(tool)


# --- run_query: text mode LLM response ---


@pytest.mark.asyncio
async def test_run_query_text_mode_prints_sentences(capsys: pytest.CaptureFixture[str]) -> None:
    config = _make_config()
    db = _make_db()  # type: ignore[assignment]

    async def _fake_stream(*_a, **_kw):
        yield "Hello there."
        yield "How are you?"

    with patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream):
        await run_query("hi", config, db, output_mode="text")  # type: ignore[arg-type]

    captured = capsys.readouterr()
    assert "Hello there." in captured.out
    assert "How are you?" in captured.out


@pytest.mark.asyncio
async def test_run_query_voice_mode_speaks_sentences() -> None:
    config = _make_config()
    db = _make_db()  # type: ignore[assignment]

    async def _fake_stream(*_a, **_kw):
        yield "Hello there."

    with (
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch("rex.daemon.pipeline.tts.speak", new_callable=AsyncMock) as mock_speak,
    ):
        await run_query("hi", config, db, output_mode="voice")

    mock_speak.assert_called_once_with("Hello there.", config.tts)


# --- run_query: read tool ---


@pytest.mark.asyncio
async def test_run_query_read_tool_runs_silently() -> None:
    config = _make_config()
    db = _make_db()  # type: ignore[assignment]
    tool_call = ToolCallRequest(id="t1", name="read_file", args={"path": "/tmp/x.txt"})

    async def _fake_stream(*_a, **_kw):
        yield tool_call

    fake_tool = MagicMock()
    fake_tool.trust = "read"
    fake_tool.run.return_value = ToolResult(output="file contents")

    with (
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch("rex.daemon.pipeline.tts.speak", new_callable=AsyncMock) as mock_speak,
        patch.dict("rex.daemon.pipeline.REGISTRY", {"read_file": fake_tool}),
    ):
        await run_query("read it", config, db, output_mode="voice")  # type: ignore[arg-type]

    fake_tool.run.assert_called_once()
    spoken = [c.args[0] for c in mock_speak.call_args_list]
    assert "file contents" in spoken


# --- run_query: write tool text mode confirm yes/no ---


@pytest.mark.asyncio
async def test_run_query_write_tool_text_confirms_yes() -> None:
    config = _make_config()
    db = _make_db()  # type: ignore[assignment]
    tool_call = ToolCallRequest(id="t2", name="write_file", args={"path": "/tmp/x.txt"})

    async def _fake_stream(*_a, **_kw):
        yield tool_call

    fake_tool = MagicMock()
    fake_tool.trust = "write"
    fake_tool.run.return_value = ToolResult(output="Written 0 bytes")

    with (
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch("rex.daemon.pipeline.confirm_text", new_callable=AsyncMock, return_value=True),
        patch.dict("rex.daemon.pipeline.REGISTRY", {"write_file": fake_tool}),
    ):
        await run_query("write it", config, db, output_mode="text")  # type: ignore[arg-type]

    fake_tool.run.assert_called_once()


@pytest.mark.asyncio
async def test_run_query_write_tool_text_confirms_no(capsys: pytest.CaptureFixture[str]) -> None:
    config = _make_config()
    db = _make_db()  # type: ignore[assignment]
    tool_call = ToolCallRequest(id="t3", name="write_file", args={"path": "/tmp/x.txt"})

    async def _fake_stream(*_a, **_kw):
        yield tool_call

    fake_tool = MagicMock()
    fake_tool.trust = "write"

    with (
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch("rex.daemon.pipeline.confirm_text", new_callable=AsyncMock, return_value=False),
        patch.dict("rex.daemon.pipeline.REGISTRY", {"write_file": fake_tool}),
    ):
        await run_query("write it", config, db, output_mode="text")  # type: ignore[arg-type]

    fake_tool.run.assert_not_called()
    captured = capsys.readouterr()
    assert "Cancelled" in captured.out


# --- run_query: write tool voice mode calls on_write_tool ---


@pytest.mark.asyncio
async def test_run_query_write_tool_voice_calls_on_write_tool() -> None:
    config = _make_config()
    db = _make_db()  # type: ignore[assignment]
    tool_call = ToolCallRequest(id="t4", name="shell", args={"command": "ls"})

    async def _fake_stream(*_a, **_kw):
        yield tool_call

    fake_tool = MagicMock()
    fake_tool.trust = "execute"
    on_write_tool = AsyncMock()

    with (
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch.dict("rex.daemon.pipeline.REGISTRY", {"shell": fake_tool}),
    ):
        await run_query(
            "run ls",
            config,
            db,  # type: ignore[arg-type]
            output_mode="voice",
            on_write_tool=on_write_tool,
        )

    on_write_tool.assert_called_once()
    call_args = on_write_tool.call_args[0]
    assert call_args[0] is tool_call


# --- run_query: saves user and assistant turns ---


@pytest.mark.asyncio
async def test_run_query_saves_user_and_assistant_turn() -> None:
    config = _make_config()
    db = _make_db()  # type: ignore[assignment]

    async def _fake_stream(*_a, **_kw):
        yield "Hello."

    with (
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch("rex.daemon.pipeline.tts.speak", new_callable=AsyncMock),
        patch("rex.daemon.pipeline.save_turn") as mock_save,
    ):
        await run_query("hi", config, db, output_mode="voice")  # type: ignore[arg-type]

    calls = [c.args[1] for c in mock_save.call_args_list]
    assert "user" in calls
    assert "assistant" in calls


# --- _load_project_context ---


def test_load_project_context_missing_returns_none(tmp_path: Path) -> None:
    assert _load_project_context(cwd=tmp_path) is None


def test_load_project_context_reads_file(tmp_path: Path) -> None:
    ctx_dir = tmp_path / ".rex"
    ctx_dir.mkdir()
    (ctx_dir / "context.md").write_text("My project is rex")
    result = _load_project_context(cwd=tmp_path)
    assert result == "My project is rex"


def test_load_project_context_explicit_path(tmp_path: Path) -> None:
    ctx_file = tmp_path / "custom_context.md"
    ctx_file.write_text("explicit path content")
    result = _load_project_context(explicit_path=str(ctx_file))
    assert result == "explicit path content"


def test_load_project_context_oserror_returns_none(tmp_path: Path) -> None:
    with patch("rex.daemon.pipeline.Path.read_text", side_effect=PermissionError("denied")):
        result = _load_project_context(cwd=tmp_path)
    assert result is None


# --- run_query context injection ---


@pytest.mark.asyncio
async def test_run_query_injects_facts() -> None:
    config = _make_config()
    db = init_db(":memory:")
    save_fact(db, "I use neovim")

    captured_msgs: list = []

    async def _fake_stream(msgs, *_a, **_kw):  # type: ignore[no-untyped-def]
        captured_msgs.extend(msgs)
        yield "ok."

    with patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream):
        await run_query("hi", config, db, output_mode="text")

    system_contents = " ".join(m["content"] for m in captured_msgs if m.get("role") == "system")
    assert "I use neovim" in system_contents


@pytest.mark.asyncio
async def test_run_query_injects_recent_tool_calls() -> None:
    config = _make_config()
    db = init_db(":memory:")
    turn_id = save_turn(db, "user", "previous query")
    save_tool_call(db, turn_id, "shell", '{"command":"ls"}', "ok", "completed")

    captured_msgs: list = []

    async def _fake_stream(msgs, *_a, **_kw):  # type: ignore[no-untyped-def]
        captured_msgs.extend(msgs)
        yield "done."

    with patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream):
        await run_query("hi", config, db, output_mode="text")

    system_contents = " ".join(m["content"] for m in captured_msgs if m.get("role") == "system")
    assert "shell" in system_contents


@pytest.mark.asyncio
async def test_run_query_injects_project_context(tmp_path: Path) -> None:
    config = _make_config()
    db = init_db(":memory:")
    ctx_dir = tmp_path / ".rex"
    ctx_dir.mkdir()
    (ctx_dir / "context.md").write_text("My project is rex")

    captured_msgs: list = []

    async def _fake_stream(msgs, *_a, **_kw):  # type: ignore[no-untyped-def]
        captured_msgs.extend(msgs)
        yield "ok."

    with patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream):
        await run_query("hi", config, db, output_mode="text", cwd=tmp_path)

    system_contents = " ".join(m["content"] for m in captured_msgs if m.get("role") == "system")
    assert "My project is rex" in system_contents


@pytest.mark.asyncio
async def test_run_query_no_project_context_when_file_absent(tmp_path: Path) -> None:
    config = _make_config()
    db = init_db(":memory:")

    captured_msgs: list = []

    async def _fake_stream(msgs, *_a, **_kw):  # type: ignore[no-untyped-def]
        captured_msgs.extend(msgs)
        yield "ok."

    with patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream):
        await run_query("hi", config, db, output_mode="text", cwd=tmp_path)

    system_contents = " ".join(m["content"] for m in captured_msgs if m.get("role") == "system")
    assert "Project context" not in system_contents


@pytest.mark.asyncio
async def test_run_query_empty_facts_skips_facts_block() -> None:
    config = _make_config()
    db = init_db(":memory:")

    captured_msgs: list = []

    async def _fake_stream(msgs, *_a, **_kw):  # type: ignore[no-untyped-def]
        captured_msgs.extend(msgs)
        yield "ok."

    with patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream):
        await run_query("hi", config, db, output_mode="text")

    system_contents = " ".join(m["content"] for m in captured_msgs if m.get("role") == "system")
    assert "Facts about" not in system_contents


# --- _format_tool_result: uncovered branches ---


def test_format_tool_result_clipboard_read_with_content() -> None:
    tool = ToolCallRequest(id="x", name="clipboard_read", args={})
    result = ToolResult(output="some text")
    assert "Clipboard: some text" in _format_tool_result(tool, result)


def test_format_tool_result_clipboard_read_truncates_long_content() -> None:
    tool = ToolCallRequest(id="x", name="clipboard_read", args={})
    result = ToolResult(output="x" * 400)
    formatted = _format_tool_result(tool, result)
    assert formatted.endswith("…")


def test_format_tool_result_web_search() -> None:
    tool = ToolCallRequest(id="x", name="web_search", args={})
    result = ToolResult(output="search results")
    assert _format_tool_result(tool, result) == "search results"


def test_format_tool_result_web_search_truncates() -> None:
    tool = ToolCallRequest(id="x", name="web_search", args={})
    result = ToolResult(output="y" * 400)
    assert _format_tool_result(tool, result).endswith("…")


# --- _confirmation_prompt: uncovered branch ---


def test_confirmation_prompt_clipboard_write() -> None:
    tool = ToolCallRequest(id="x", name="clipboard_write", args={"text": "hello"})
    assert _confirmation_prompt(tool) == "Copy to clipboard: hello?"


# --- _load_project_context: explicit path not found warning ---


def test_load_project_context_explicit_path_missing_returns_none(tmp_path: Path) -> None:
    result = _load_project_context(explicit_path=str(tmp_path / "nonexistent.md"))
    assert result is None


# --- confirm_text ---


@pytest.mark.asyncio
async def test_confirm_text_yes_returns_true() -> None:
    with patch("builtins.input", return_value="y"):
        result = await confirm_text("Do it?")
    assert result is True


@pytest.mark.asyncio
async def test_confirm_text_no_returns_false() -> None:
    with patch("builtins.input", return_value="n"):
        result = await confirm_text("Do it?")
    assert result is False


# --- _run_tool_inline: unknown tool ---


@pytest.mark.asyncio
async def test_run_tool_inline_unknown_tool_prints_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = _make_config()
    db = init_db(":memory:")
    tool_call = ToolCallRequest(id="t9", name="unknown_tool", args={})
    turn_id = save_turn(db, "user", "do something")

    with patch.dict("rex.daemon.pipeline.REGISTRY", {}):
        await _run_tool_inline(tool_call, config, db, turn_id, "text")

    captured = capsys.readouterr()
    assert "don't know" in captured.out


@pytest.mark.asyncio
async def test_run_tool_inline_unknown_tool_speaks_in_voice_mode() -> None:
    config = _make_config()
    db = init_db(":memory:")
    tool_call = ToolCallRequest(id="t9b", name="unknown_tool", args={})
    turn_id = save_turn(db, "user", "do something")

    with (
        patch.dict("rex.daemon.pipeline.REGISTRY", {}),
        patch("rex.daemon.pipeline.tts.speak", new_callable=AsyncMock) as mock_speak,
    ):
        await _run_tool_inline(tool_call, config, db, turn_id, "voice")

    mock_speak.assert_called_once()
    assert "don't know" in mock_speak.call_args[0][0]


@pytest.mark.asyncio
async def test_run_tool_inline_bad_args_prints_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config = _make_config()
    db = init_db(":memory:")
    tool_call = ToolCallRequest(id="t10", name="read_file", args={})
    turn_id = save_turn(db, "user", "read it")

    fake_tool = MagicMock()
    fake_tool.trust = "read"
    fake_tool.run.side_effect = KeyError("path")

    with patch.dict("rex.daemon.pipeline.REGISTRY", {"read_file": fake_tool}):
        await _run_tool_inline(tool_call, config, db, turn_id, "text")

    captured = capsys.readouterr()
    assert "went wrong" in captured.out


@pytest.mark.asyncio
async def test_run_tool_inline_bad_args_speaks_in_voice_mode() -> None:
    config = _make_config()
    db = init_db(":memory:")
    tool_call = ToolCallRequest(id="t10b", name="read_file", args={})
    turn_id = save_turn(db, "user", "read it")

    fake_tool = MagicMock()
    fake_tool.trust = "read"
    fake_tool.run.side_effect = TypeError("bad arg")

    with (
        patch.dict("rex.daemon.pipeline.REGISTRY", {"read_file": fake_tool}),
        patch("rex.daemon.pipeline.tts.speak", new_callable=AsyncMock) as mock_speak,
    ):
        await _run_tool_inline(tool_call, config, db, turn_id, "voice")

    mock_speak.assert_called_once()
    assert "went wrong" in mock_speak.call_args[0][0]

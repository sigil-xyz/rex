import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from rex.config import NotificationConfig, RexConfig
from rex.daemon.audio import AudioRecorder
from rex.daemon.llm import ToolCallRequest
from rex.daemon.main import RexDaemon, _confirmation_prompt, _notify, get_socket_path
from rex.daemon.stt import Transcriber
from rex.daemon.tools import ToolResult


def test_get_socket_path_uses_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/999")
    assert get_socket_path() == Path("/run/user/999/rex.sock")


def test_get_socket_path_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    assert get_socket_path() == Path("/tmp/rex.sock")


@pytest.mark.asyncio
async def test_notify_skipped_when_disabled() -> None:
    config = NotificationConfig(enabled=False)
    with patch("rex.daemon.main.asyncio.create_subprocess_exec") as mock_exec:
        await _notify("hello", config)
    mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_notify_calls_correct_command_on_linux() -> None:
    config = NotificationConfig(enabled=True, timeout=3000)
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", b""))
    with (
        patch("rex.daemon.main.platform.system", return_value="Linux"),
        patch("rex.daemon.main.asyncio.create_subprocess_exec", return_value=proc) as mock_exec,
    ):
        await _notify("hello", config)
    args = mock_exec.call_args[0]
    assert "notify-send" in args


@pytest.mark.asyncio
async def test_notify_calls_osascript_on_macos() -> None:
    config = NotificationConfig(enabled=True, timeout=3000)
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", b""))
    with (
        patch("rex.daemon.main.platform.system", return_value="Darwin"),
        patch("rex.daemon.main.asyncio.create_subprocess_exec", return_value=proc) as mock_exec,
    ):
        await _notify("hello", config)
    args = mock_exec.call_args[0]
    assert "osascript" in args


def _make_daemon() -> RexDaemon:
    config = RexConfig()
    config.memory_db = ":memory:"
    recorder = MagicMock(spec=AudioRecorder)
    transcriber = MagicMock(spec=Transcriber)
    return RexDaemon(config, recorder, transcriber)


# --- confirmation prompt ---


def test_confirmation_prompt_shell() -> None:
    tool = ToolCallRequest(id="c1", name="shell", args={"command": "ls -la"})
    assert _confirmation_prompt(tool) == "Run: ls -la?"


def test_confirmation_prompt_clipboard_write() -> None:
    tool = ToolCallRequest(id="c1", name="clipboard_write", args={"text": "hello world"})
    assert "Copy to clipboard" in _confirmation_prompt(tool)
    assert "hello world" in _confirmation_prompt(tool)


def test_confirmation_prompt_generic() -> None:
    tool = ToolCallRequest(id="c1", name="web_search", args={"query": "arch"})
    assert "web_search" in _confirmation_prompt(tool)


# --- dispatch & basic state ---


@pytest.mark.asyncio
async def test_dispatch_unknown_command_logs_warning() -> None:
    daemon = _make_daemon()
    await daemon._dispatch("unknown")


@pytest.mark.asyncio
async def test_on_start_sets_recording() -> None:
    daemon = _make_daemon()
    await daemon._on_start()
    assert daemon._recording is True
    daemon._recorder.start.assert_called_once()


@pytest.mark.asyncio
async def test_on_start_ignores_duplicate() -> None:
    daemon = _make_daemon()
    await daemon._on_start()
    await daemon._on_start()
    daemon._recorder.start.assert_called_once()


@pytest.mark.asyncio
async def test_on_stop_ignored_when_not_recording() -> None:
    daemon = _make_daemon()
    await daemon._on_stop()
    daemon._recorder.stop.assert_not_called()


@pytest.mark.asyncio
async def test_on_stop_runs_pipeline() -> None:
    daemon = _make_daemon()
    daemon._recorder.stop.return_value = np.zeros(16000, dtype=np.float32)
    daemon._transcriber.transcribe.return_value = "hello"

    async def _fake_stream(*_a, **_kw):
        yield "Hello there."

    await daemon._on_start()

    with (
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch("rex.daemon.pipeline.tts.speak", new_callable=AsyncMock),
        patch("rex.daemon.main._notify", new_callable=AsyncMock),
    ):
        await daemon._on_stop()

    assert daemon._recording is False


# --- read tool: immediate execution ---


@pytest.mark.asyncio
async def test_on_query_read_tool_runs_immediately() -> None:
    daemon = _make_daemon()
    daemon._recorder.stop.return_value = np.zeros(16000, dtype=np.float32)
    daemon._transcriber.transcribe.return_value = "read my file"

    tool_call = ToolCallRequest(id="c1", name="read_file", args={"path": "/tmp/x.txt"})

    async def _fake_stream(*_a, **_kw):
        yield tool_call

    fake_tool = MagicMock()
    fake_tool.trust = "read"
    fake_tool.run.return_value = ToolResult(output="file contents")

    await daemon._on_start()
    with (
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch("rex.daemon.pipeline.tts.speak", new_callable=AsyncMock) as mock_speak,
        patch("rex.daemon.main._notify", new_callable=AsyncMock),
        patch.dict("rex.daemon.pipeline.REGISTRY", {"read_file": fake_tool}),
    ):
        await daemon._on_stop()

    # tool ran, result spoken locally — no second LLM call
    fake_tool.run.assert_called_once_with({"path": "/tmp/x.txt"})
    assert daemon._pending_tool is None
    spoken = [c.args[0] for c in mock_speak.call_args_list]
    assert "file contents" in spoken


# --- write/execute tool: confirmation gate ---


@pytest.mark.asyncio
async def test_on_query_write_tool_asks_confirmation() -> None:
    daemon = _make_daemon()
    daemon._recorder.stop.return_value = np.zeros(16000, dtype=np.float32)
    daemon._transcriber.transcribe.return_value = "copy something"

    tool_call = ToolCallRequest(id="c2", name="clipboard_write", args={"text": "hello"})

    async def _fake_stream(*_a, **_kw):
        yield tool_call

    fake_tool = MagicMock()
    fake_tool.trust = "write"

    await daemon._on_start()
    with (
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch("rex.daemon.main.tts.speak", new_callable=AsyncMock) as mock_speak,
        patch.dict("rex.daemon.pipeline.REGISTRY", {"clipboard_write": fake_tool}),
    ):
        await daemon._on_stop()

    # confirmation prompt spoken, tool is pending
    assert daemon._pending_tool is tool_call
    spoken = [c.args[0] for c in mock_speak.call_args_list]
    assert any("clipboard" in s.lower() for s in spoken)

    # clean up background timeout task
    if daemon._confirmation_task:
        daemon._confirmation_task.cancel()


# --- confirmation: yes → runs tool ---


@pytest.mark.asyncio
async def test_on_confirmation_yes_runs_tool() -> None:
    daemon = _make_daemon()
    tool_call = ToolCallRequest(id="c3", name="shell", args={"command": "ls"})
    daemon._pending_tool = tool_call
    daemon._pending_turn_id = 1

    fake_tool = MagicMock()
    fake_tool.run.return_value = ToolResult(output="file1\nfile2")

    with (
        patch("rex.daemon.main.tts.speak", new_callable=AsyncMock) as mock_speak,
        patch("rex.daemon.main._notify", new_callable=AsyncMock),
        patch.dict("rex.daemon.main.REGISTRY", {"shell": fake_tool}),
    ):
        await daemon._on_confirmation("yes please")

    fake_tool.run.assert_called_once()
    assert daemon._pending_tool is None
    spoken = [c.args[0] for c in mock_speak.call_args_list]
    assert "file1\nfile2" in spoken


# --- confirmation: no → cancels ---


@pytest.mark.asyncio
async def test_on_confirmation_no_cancels() -> None:
    daemon = _make_daemon()
    tool_call = ToolCallRequest(id="c4", name="shell", args={"command": "ls"})
    daemon._pending_tool = tool_call
    daemon._pending_turn_id = 2

    with patch("rex.daemon.main.tts.speak", new_callable=AsyncMock) as mock_speak:
        await daemon._on_confirmation("no cancel that")

    assert daemon._pending_tool is None
    spoken = [c.args[0] for c in mock_speak.call_args_list]
    assert any("Cancel" in s for s in spoken)


# --- confirmation timeout ---


@pytest.mark.asyncio
async def test_confirmation_timeout_cancels() -> None:
    daemon = _make_daemon()
    tool_call = ToolCallRequest(id="c5", name="shell", args={"command": "ls"})
    daemon._pending_tool = tool_call
    daemon._pending_turn_id = 3

    with (
        patch("rex.daemon.main.asyncio.sleep", new_callable=AsyncMock),
        patch("rex.daemon.main.tts.speak", new_callable=AsyncMock) as mock_speak,
    ):
        await daemon._confirmation_timeout()

    assert daemon._pending_tool is None
    spoken = [c.args[0] for c in mock_speak.call_args_list]
    assert any("Cancel" in s for s in spoken)


# --- shutdown ---


@pytest.mark.asyncio
async def test_shutdown_removes_socket(tmp_path: Path) -> None:
    daemon = _make_daemon()
    sock = tmp_path / "rex.sock"
    sock.touch()
    daemon._socket_path = sock
    daemon._server = MagicMock()
    daemon._server.close = MagicMock()
    daemon._server.wait_closed = AsyncMock()

    await daemon.shutdown()
    assert not sock.exists()


# --- _on_start cancels pending confirmation ---


@pytest.mark.asyncio
async def test_on_start_cancels_pending_confirmation_task() -> None:
    daemon = _make_daemon()
    # Simulate a confirmation task being active when PTT is pressed
    fake_task = MagicMock(spec=asyncio.Task)
    daemon._confirmation_task = fake_task  # type: ignore[assignment]

    await daemon._on_start()

    fake_task.cancel.assert_called_once()
    assert daemon._confirmation_task is None


# --- _on_stop routes to confirmation when pending ---


@pytest.mark.asyncio
async def test_on_stop_routes_to_confirmation_when_pending() -> None:
    daemon = _make_daemon()
    daemon._recorder.stop.return_value = np.zeros(1, dtype=np.float32)
    daemon._transcriber.transcribe.return_value = "yes"

    tool_call = ToolCallRequest(id="c9", name="shell", args={"command": "ls"})
    daemon._pending_tool = tool_call
    daemon._pending_turn_id = 1

    fake_tool = MagicMock()
    fake_tool.run.return_value = ToolResult(output="file list")

    await daemon._on_start()
    with (
        patch("rex.daemon.main.tts.speak", new_callable=AsyncMock),
        patch("rex.daemon.main._notify", new_callable=AsyncMock),
        patch.dict("rex.daemon.main.REGISTRY", {"shell": fake_tool}),
    ):
        await daemon._on_stop()

    fake_tool.run.assert_called_once()


# --- dispatch: start/stop commands ---


@pytest.mark.asyncio
async def test_dispatch_start_calls_on_start() -> None:
    daemon = _make_daemon()
    with patch.object(daemon, "_on_start", new_callable=AsyncMock) as mock_start:
        await daemon._dispatch("start")
    mock_start.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_stop_calls_on_stop() -> None:
    daemon = _make_daemon()
    with patch.object(daemon, "_on_stop", new_callable=AsyncMock) as mock_stop:
        await daemon._dispatch("stop")
    mock_stop.assert_called_once()


# --- _handle_client ---


@pytest.mark.asyncio
async def test_handle_client_reads_and_dispatches() -> None:
    daemon = _make_daemon()
    reader = MagicMock(spec=asyncio.StreamReader)
    writer = MagicMock(spec=asyncio.StreamWriter)
    reader.readline = AsyncMock(return_value=b"start\n")
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    with patch.object(daemon, "_on_start", new_callable=AsyncMock) as mock_start:
        await daemon._handle_client(reader, writer)

    mock_start.assert_called_once()
    writer.close.assert_called_once()


# --- _recording_timeout ---


@pytest.mark.asyncio
async def test_recording_timeout_forces_stop() -> None:
    daemon = _make_daemon()
    daemon._recording = True
    daemon._recorder.stop.return_value = np.zeros(1, dtype=np.float32)
    daemon._transcriber.transcribe.return_value = "timeout transcript"

    async def _fake_stream(*_a, **_kw):
        yield "Response."

    with (
        patch("rex.daemon.main.asyncio.sleep", new_callable=AsyncMock),
        patch("rex.daemon.pipeline.llm.respond_streaming_msgs", side_effect=_fake_stream),
        patch("rex.daemon.pipeline.tts.speak", new_callable=AsyncMock),
        patch("rex.daemon.main._notify", new_callable=AsyncMock),
    ):
        await daemon._recording_timeout()

    assert daemon._recording is False

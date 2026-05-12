import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from rex.config import NotificationConfig, RexConfig
from rex.daemon.audio import AudioRecorder
from rex.daemon.main import RexDaemon, _notify, get_socket_path
from rex.daemon.stt import Transcriber


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
async def test_notify_calls_notify_send_when_enabled() -> None:
    config = NotificationConfig(enabled=True, timeout=3000)
    proc = MagicMock()
    with patch("rex.daemon.main.asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        await _notify("hello", config)
    mock_exec.assert_called_once()
    args = mock_exec.call_args[0]
    assert "notify-send" in args


def _make_daemon() -> RexDaemon:
    config = RexConfig()
    recorder = MagicMock(spec=AudioRecorder)
    transcriber = MagicMock(spec=Transcriber)
    return RexDaemon(config, recorder, transcriber)


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

    await daemon._on_start()

    with patch("rex.daemon.main.llm.respond", return_value="Hello. How can I help?"):
        with patch("rex.daemon.main.tts.speak", new_callable=AsyncMock):
            with patch("rex.daemon.main._notify", new_callable=AsyncMock):
                await daemon._on_stop()

    assert daemon._recording is False


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

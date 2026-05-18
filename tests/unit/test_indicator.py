"""Tests for rex.cli.indicator — client, async client, and entry-point logic.

The GTK4 daemon (_run_daemon) is excluded: it requires a running Wayland
display and cannot be unit-tested in CI.
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import rex.cli.indicator as ind

# ---------------------------------------------------------------------------
# _socket_path
# ---------------------------------------------------------------------------


def test_socket_path_uses_xdg_runtime_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert ind._socket_path() == tmp_path / "rex-indicator.sock"


def test_socket_path_falls_back_to_tmp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    assert ind._socket_path() == Path("/tmp") / "rex-indicator.sock"


# ---------------------------------------------------------------------------
# _send (sync client)
# ---------------------------------------------------------------------------


def test_send_returns_false_when_no_socket(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert ind._send("show listening") is False


def test_send_returns_true_over_live_socket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    sock_path = tmp_path / "rex-indicator.sock"

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(1)
    srv.setblocking(False)

    try:
        result = ind._send("show listening", timeout=1.0)
        # Accept the connection so the client doesn't get ECONNRESET
        try:
            conn, _ = srv.accept()
            conn.close()
        except BlockingIOError:
            pass
        assert result is True
    finally:
        srv.close()


def test_send_returns_false_on_connection_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    sock_path = tmp_path / "rex-indicator.sock"
    # Create socket file so path.exists() passes, but nobody is listening
    sock_path.touch()
    # _send should catch OSError (ENOTSOCK / ECONNREFUSED) and return False
    assert ind._send("hide") is False


# ---------------------------------------------------------------------------
# show / hide (thin wrappers)
# ---------------------------------------------------------------------------


def test_show_delegates_to_send() -> None:
    with patch.object(ind, "_send", return_value=True) as mock_send:
        result = ind.show("listening")
    mock_send.assert_called_once_with("show listening")
    assert result is True


def test_hide_delegates_to_send() -> None:
    with patch.object(ind, "_send", return_value=False) as mock_send:
        result = ind.hide()
    mock_send.assert_called_once_with("hide")
    assert result is False


# ---------------------------------------------------------------------------
# async_show / async_hide — fire-and-forget, must not raise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_show_silently_ignores_connection_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    # Socket does not exist → connection error → silently ignored
    await ind.async_show("listening")


@pytest.mark.asyncio
async def test_async_hide_silently_ignores_connection_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    await ind.async_hide()


@pytest.mark.asyncio
async def test_async_show_sends_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    received: list[bytes] = []

    async def _serve() -> None:
        sock_path = tmp_path / "rex-indicator.sock"
        server = await asyncio.start_unix_server(
            lambda r, w: _handler(r, w, received), path=str(sock_path)
        )
        async with server:
            await asyncio.wait_for(server.serve_forever(), timeout=1.0)

    async def _handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        buf: list[bytes],
    ) -> None:
        data = await reader.read(256)
        buf.append(data)
        writer.close()

    server_task = asyncio.create_task(_serve())
    await asyncio.sleep(0.05)  # let server bind

    await ind.async_show("thinking")
    await asyncio.sleep(0.05)

    server_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, TimeoutError):
        await server_task

    assert any(b"show thinking" in msg for msg in received)


# ---------------------------------------------------------------------------
# indicator_main — entry-point CLI dispatch
# ---------------------------------------------------------------------------


def test_indicator_main_hide_calls_hide(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-indicator", "hide"])
    with patch.object(ind, "hide", return_value=True) as mock_hide:
        ind.indicator_main()
    mock_hide.assert_called_once()


def test_indicator_main_quit_sends_quit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-indicator", "quit"])
    with patch.object(ind, "_send", return_value=True) as mock_send:
        ind.indicator_main()
    mock_send.assert_called_once_with("quit")


def test_indicator_main_show_when_daemon_running(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-indicator", "show", "listening"])
    with patch.object(ind, "show", return_value=True) as mock_show:
        ind.indicator_main()
    mock_show.assert_called_once_with("listening")


def test_indicator_main_show_starts_daemon_when_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-indicator", "show", "thinking"])
    # show() always returns False → daemon not running → auto-start → still fails → log + return
    with (
        patch.object(ind, "show", return_value=False),
        patch.object(ind, "_auto_start") as mock_start,
        patch("time.sleep"),
    ):
        ind.indicator_main()
    mock_start.assert_called_once()


def test_indicator_main_no_args_starts_daemon(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-indicator"])
    with patch.object(ind, "_run_daemon") as mock_daemon:
        ind.indicator_main()
    mock_daemon.assert_called_once()


def test_indicator_main_invalid_args_exits_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-indicator", "unknown"])
    with pytest.raises(SystemExit) as exc_info:
        ind.indicator_main()
    assert exc_info.value.code == 1


def test_indicator_main_show_succeeds_on_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["rex-indicator", "show", "done"])
    # First call returns False (not running), second returns True (started)
    show_results = iter([False, True])
    with (
        patch.object(ind, "show", side_effect=show_results),
        patch.object(ind, "_auto_start"),
        patch("time.sleep"),
    ):
        ind.indicator_main()


# ---------------------------------------------------------------------------
# _auto_start
# ---------------------------------------------------------------------------


def test_auto_start_launches_subprocess() -> None:
    with patch("subprocess.Popen") as mock_popen:
        ind._auto_start()
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert "rex.cli.indicator" in " ".join(args)


# ---------------------------------------------------------------------------
# async_hide: success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_hide_sends_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    received: list[bytes] = []

    async def _handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        data = await reader.read(256)
        received.append(data)
        writer.close()

    async def _serve() -> None:
        sock_path = tmp_path / "rex-indicator.sock"
        server = await asyncio.start_unix_server(_handler, path=str(sock_path))
        async with server:
            await asyncio.wait_for(server.serve_forever(), timeout=1.0)

    server_task = asyncio.create_task(_serve())
    await asyncio.sleep(0.05)

    await ind.async_hide()
    await asyncio.sleep(0.05)

    server_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, TimeoutError):
        await server_task

    assert any(b"hide" in msg for msg in received)

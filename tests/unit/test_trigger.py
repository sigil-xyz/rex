from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rex.cli.trigger import get_socket_path, main, socket_connection


def test_get_socket_path_uses_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1234")
    assert get_socket_path() == Path("/run/user/1234/rex.sock")


def test_get_socket_path_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    assert get_socket_path() == Path("/tmp/rex.sock")


@pytest.mark.asyncio
async def test_socket_connection_sends_command() -> None:
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()

    with patch("rex.cli.trigger.asyncio.open_unix_connection", return_value=(MagicMock(), writer)):
        await socket_connection("start")

    writer.write.assert_called_once_with(b"start\n")


def test_main_invalid_command(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["rex-trigger", "invalid"]), pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "usage" in capsys.readouterr().err


def test_main_missing_command() -> None:
    with patch("sys.argv", ["rex-trigger"]), pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_file_not_found(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("sys.argv", ["rex-trigger", "start"]),
        patch("rex.cli.trigger.socket_connection", side_effect=FileNotFoundError),
        patch("rex.cli.trigger.asyncio.run", side_effect=FileNotFoundError),
        pytest.raises(SystemExit) as exc,
    ):
        main()
    assert exc.value.code == 1
    assert "not running" in capsys.readouterr().err


def test_main_connection_refused(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("sys.argv", ["rex-trigger", "stop"]),
        patch("rex.cli.trigger.socket_connection", side_effect=ConnectionRefusedError),
        patch("rex.cli.trigger.asyncio.run", side_effect=ConnectionRefusedError),
        pytest.raises(SystemExit) as exc,
    ):
        main()
    assert exc.value.code == 1
    assert "refused" in capsys.readouterr().err

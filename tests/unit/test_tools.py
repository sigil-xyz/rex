import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from rex.daemon.tools import (
    REGISTRY,
    _clipboard_read,
    _clipboard_write,
    _read_file,
    _shell,
    _web_search,
    _write_file,
    get_tool_schemas,
)

# --- read_file ---


def test_read_file_returns_content(tmp_path: Path) -> None:
    f = tmp_path / "hello.txt"
    f.write_text("hello world")
    with patch("rex.daemon.tools._HOME", tmp_path):
        result = _read_file({"path": str(f)})
    assert result.error is None
    assert result.output == "hello world"


def test_read_file_rejects_outside_home(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    home = tmp_path / "home"
    home.mkdir()
    with patch("rex.daemon.tools._HOME", home):
        result = _read_file({"path": str(outside)})
    assert result.error is not None
    assert "outside home directory" in result.error


def test_read_file_truncates_large_files(tmp_path: Path) -> None:
    f = tmp_path / "big.txt"
    f.write_text("x" * 5000)
    with patch("rex.daemon.tools._HOME", tmp_path):
        result = _read_file({"path": str(f)})
    assert result.error is None
    assert len(result.output) < 5000
    assert "truncated" in result.output


def test_read_file_missing(tmp_path: Path) -> None:
    with patch("rex.daemon.tools._HOME", tmp_path):
        result = _read_file({"path": str(tmp_path / "nope.txt")})
    assert result.error is not None
    assert "not found" in result.error


def test_read_file_directory(tmp_path: Path) -> None:
    with patch("rex.daemon.tools._HOME", tmp_path):
        result = _read_file({"path": str(tmp_path)})
    assert result.error is not None
    assert "directory" in result.error


# --- shell ---


def test_shell_captures_output() -> None:
    result = _shell({"command": "echo hello"})
    assert result.error is None
    assert "hello" in result.output


def test_shell_captures_stderr() -> None:
    result = _shell({"command": "echo err >&2"})
    assert "err" in result.output


def test_shell_rejects_rm_rf() -> None:
    result = _shell({"command": "rm -rf /"})
    assert result.error is not None
    assert "blocked" in result.error


def test_shell_rejects_sudo() -> None:
    result = _shell({"command": "sudo whoami"})
    assert result.error is not None
    assert "blocked" in result.error


def test_shell_rejects_fork_bomb() -> None:
    result = _shell({"command": ":(){ :|:& };:"})
    assert result.error is not None
    assert "blocked" in result.error


def test_shell_truncates_large_output() -> None:
    result = _shell({"command": "python3 -c \"print('x' * 5000)\""})
    assert result.error is None
    assert len(result.output) < 5100
    assert "truncated" in result.output


def test_shell_timeout() -> None:
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 30)):
        result = _shell({"command": "sleep 60"})
    assert result.error is not None
    assert "timed out" in result.error


def test_shell_no_output_returns_placeholder() -> None:
    result = _shell({"command": "true"})
    assert result.error is None
    assert result.output == "(no output)"


# --- web_search ---


def _ddgr_output(items: list[dict]) -> MagicMock:
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = json.dumps(items)
    proc.stderr = ""
    return proc


def test_web_search_parses_ddgr_output() -> None:
    items = [
        {"title": "Arch Linux", "url": "https://archlinux.org", "abstract": "A simple distro"},
        {"title": "AUR", "url": "https://aur.archlinux.org", "abstract": "User repository"},
    ]
    with patch("subprocess.run", return_value=_ddgr_output(items)):
        result = _web_search({"query": "arch linux"})
    assert result.error is None
    assert "Arch Linux" in result.output
    assert "https://archlinux.org" in result.output
    assert "AUR" in result.output


def test_web_search_no_results() -> None:
    with patch("subprocess.run", return_value=_ddgr_output([])):
        result = _web_search({"query": "xyzzy nothing happens"})
    assert result.error is None
    assert "No results" in result.output


def test_web_search_ddgr_not_found() -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _web_search({"query": "test"})
    assert result.error is not None
    assert "ddgr not found" in result.error


def test_web_search_invalid_json() -> None:
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = "not json"
    proc.stderr = ""
    with patch("subprocess.run", return_value=proc):
        result = _web_search({"query": "test"})
    assert result.error is not None
    assert "invalid JSON" in result.error


# --- clipboard ---


def _wl_proc(stdout: str = "", returncode: int = 0, stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def test_clipboard_read_returns_content() -> None:
    with patch("subprocess.run", return_value=_wl_proc(stdout="clipped text")):
        result = _clipboard_read({})
    assert result.error is None
    assert result.output == "clipped text"


def test_clipboard_read_wl_paste_missing() -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _clipboard_read({})
    assert result.error is not None
    assert "wl-paste not found" in result.error


def test_clipboard_write_success() -> None:
    with patch("subprocess.run", return_value=_wl_proc()) as mock_run:
        result = _clipboard_write({"text": "write me"})
    assert result.error is None
    assert "Copied" in result.output
    assert mock_run.call_args[1]["input"] == "write me"


def test_clipboard_write_wl_copy_missing() -> None:
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _clipboard_write({"text": "hello"})
    assert result.error is not None
    assert "wl-copy not found" in result.error


# --- write_file ---


def test_write_file_creates_file(tmp_path: Path) -> None:
    f = tmp_path / "out.txt"
    with patch("rex.daemon.tools._HOME", tmp_path):
        result = _write_file({"path": str(f), "content": "hello"})
    assert result.error is None
    assert f.read_text() == "hello"
    assert "5 characters" in result.output


def test_write_file_creates_parent_dirs(tmp_path: Path) -> None:
    f = tmp_path / "a" / "b" / "out.txt"
    with patch("rex.daemon.tools._HOME", tmp_path):
        result = _write_file({"path": str(f), "content": "data"})
    assert result.error is None
    assert f.read_text() == "data"


def test_write_file_rejects_outside_home(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    home = tmp_path / "home"
    home.mkdir()
    with patch("rex.daemon.tools._HOME", home):
        result = _write_file({"path": str(outside), "content": "x"})
    assert result.error is not None
    assert "outside home directory" in result.error


def test_write_file_overwrites_existing(tmp_path: Path) -> None:
    f = tmp_path / "existing.txt"
    f.write_text("old content")
    with patch("rex.daemon.tools._HOME", tmp_path):
        result = _write_file({"path": str(f), "content": "new content"})
    assert result.error is None
    assert f.read_text() == "new content"


# --- registry & schemas ---


def test_registry_has_all_tools() -> None:
    assert set(REGISTRY.keys()) == {
        "read_file",
        "write_file",
        "clipboard_read",
        "clipboard_write",
        "shell",
        "web_search",
    }


def test_get_tool_schemas_returns_openai_format() -> None:
    schemas = get_tool_schemas()
    assert len(schemas) == 6
    for schema in schemas:
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

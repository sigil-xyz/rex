from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rex.config import TtsConfig
from rex.daemon.tts import clean_for_speech, speak


@pytest.mark.asyncio
async def test_speak_calls_piper_and_plays_audio() -> None:
    piper = MagicMock()
    piper.communicate = AsyncMock(return_value=(b"\x00" * 1024, b""))
    piper.returncode = 0

    with (
        patch("rex.daemon.tts.asyncio.create_subprocess_exec", return_value=piper),
        patch("rex.daemon.tts._play_raw_pcm") as mock_play,
    ):
        await speak("hello", TtsConfig())
        mock_play.assert_called_once_with(b"\x00" * 1024)


@pytest.mark.asyncio
async def test_speak_logs_warning_on_piper_failure() -> None:
    piper = MagicMock()
    piper.communicate = AsyncMock(return_value=(b"", b""))
    piper.returncode = 1

    with (
        patch("rex.daemon.tts.asyncio.create_subprocess_exec", return_value=piper),
        patch("rex.daemon.tts._play_raw_pcm") as mock_play,
    ):
        await speak("hello", TtsConfig())
        mock_play.assert_not_called()


@pytest.mark.asyncio
async def test_speak_logs_warning_on_playback_failure() -> None:
    piper = MagicMock()
    piper.communicate = AsyncMock(return_value=(b"\x00" * 512, b""))
    piper.returncode = 0

    with (
        patch("rex.daemon.tts.asyncio.create_subprocess_exec", return_value=piper),
        patch("rex.daemon.tts._play_raw_pcm", side_effect=Exception("sounddevice error")),
    ):
        # should not raise — warning is logged instead
        await speak("hello", TtsConfig())


# ---------------------------------------------------------------------------
# clean_for_speech
# ---------------------------------------------------------------------------


def test_clean_strips_bold() -> None:
    assert clean_for_speech("this is **important**") == "this is important"


def test_clean_strips_italic() -> None:
    assert clean_for_speech("this is *emphasized*") == "this is emphasized"


def test_clean_strips_inline_code() -> None:
    assert clean_for_speech("call `read_file` now") == "call read_file now"


def test_clean_strips_header() -> None:
    assert clean_for_speech("## Overview") == "Overview"


def test_clean_replaces_code_block() -> None:
    text = "here:\n```python\nprint('hi')\n```\ndone"
    result = clean_for_speech(text)
    assert "```" not in result
    assert "terminal" in result


def test_clean_replaces_abs_path() -> None:
    result = clean_for_speech("edit /src/rex/daemon/pipeline.py now")
    assert "/src/rex/daemon/pipeline.py" not in result
    assert "pipeline.py file" in result


def test_clean_replaces_tilde_path() -> None:
    result = clean_for_speech("check ~/.config/rex/config.toml")
    assert "~/.config" not in result
    assert "config.toml file" in result


def test_clean_converts_megabytes() -> None:
    assert "megabytes" in clean_for_speech("uses 40.3MB of memory")


def test_clean_converts_milliseconds() -> None:
    assert "milliseconds" in clean_for_speech("latency is 120ms")


def test_clean_converts_percent() -> None:
    assert "percent" in clean_for_speech("coverage is 80%")


def test_clean_converts_arrow() -> None:
    assert " then " in clean_for_speech("input → output")


def test_clean_empty_after_strip_returns_empty() -> None:
    assert clean_for_speech("   ") == ""


def test_clean_removes_stray_backtick() -> None:
    assert "`" not in clean_for_speech("the `config` key")

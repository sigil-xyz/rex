from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rex.config import TtsConfig
from rex.daemon.tts import speak


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

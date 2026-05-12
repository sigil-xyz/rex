from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rex.config import TtsConfig
from rex.daemon.tts import speak


@pytest.mark.asyncio
async def test_speak_calls_piper_and_aplay() -> None:
    piper = MagicMock()
    piper.communicate = AsyncMock(return_value=(b"\x00" * 1024, b""))
    piper.returncode = 0

    aplay = MagicMock()
    aplay.communicate = AsyncMock(return_value=(b"", b""))
    aplay.returncode = 0

    with patch("rex.daemon.tts.asyncio.create_subprocess_exec", side_effect=[piper, aplay]):
        await speak("hello", TtsConfig())


@pytest.mark.asyncio
async def test_speak_logs_warning_on_piper_failure() -> None:
    piper = MagicMock()
    piper.communicate = AsyncMock(return_value=(b"", b""))
    piper.returncode = 1

    aplay = MagicMock()
    aplay.communicate = AsyncMock(return_value=(b"", b""))
    aplay.returncode = 0

    with patch("rex.daemon.tts.asyncio.create_subprocess_exec", side_effect=[piper, aplay]):
        await speak("hello", TtsConfig())


@pytest.mark.asyncio
async def test_speak_logs_warning_on_aplay_failure() -> None:
    piper = MagicMock()
    piper.communicate = AsyncMock(return_value=(b"\x00" * 512, b""))
    piper.returncode = 0

    aplay = MagicMock()
    aplay.communicate = AsyncMock(return_value=(b"", b""))
    aplay.returncode = 1

    with patch("rex.daemon.tts.asyncio.create_subprocess_exec", side_effect=[piper, aplay]):
        await speak("hello", TtsConfig())

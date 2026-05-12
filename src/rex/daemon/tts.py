import asyncio
import logging

import numpy as np
import sounddevice as sd

from rex.config import TtsConfig

logger = logging.getLogger(__name__)

# Matches Piper's --output-raw default for most voices (e.g. lessac-medium)
_PIPER_SAMPLE_RATE = 22050


def _play_raw_pcm(raw: bytes) -> None:
    if not raw:
        return
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
    sd.play(samples, samplerate=_PIPER_SAMPLE_RATE)
    sd.wait()


async def speak(text: str, config: TtsConfig) -> None:
    logger.debug("speaking: %s", text[:50] + ("..." if len(text) > 50 else ""))

    piper = await asyncio.create_subprocess_exec(
        config.piper_bin,
        "--model",
        config.model,
        "--output-raw",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    raw_audio, _ = await piper.communicate(text.encode())

    if piper.returncode != 0:
        logger.warning("piper exited non-zero: %d", piper.returncode)
        return

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _play_raw_pcm, raw_audio)
    except Exception as e:
        logger.warning("audio playback failed: %s", e)

import asyncio
import logging

from rex.config import TtsConfig

logger = logging.getLogger(__name__)


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

    aplay = await asyncio.create_subprocess_exec(
        "aplay",
        "-r",
        "22050",
        "-f",
        "S16_LE",
        "-c",
        "1",
        stdin=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    await aplay.communicate(raw_audio)

    if aplay.returncode != 0:
        logger.warning("aplay exited non-zero: %d", aplay.returncode)

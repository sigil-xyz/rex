import asyncio
import logging
import re

import numpy as np
import sounddevice as sd

from rex.config import TtsConfig

logger = logging.getLogger(__name__)

# Matches Piper's --output-raw default for most voices (e.g. lessac-medium)
_PIPER_SAMPLE_RATE = 22050

_CODE_BLOCK = re.compile(r"```[\s\S]*?```")
_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"\*([^*]+)\*")
_HEADER = re.compile(r"#{1,6}\s+")
_ABS_PATH = re.compile(r"(?:/[\w.\-]+){2,}/(\w[\w.\-]*)")
_TILDE_PATH = re.compile(r"~/[\w./\-]+/(\w[\w.\-]*)")
_MEGABYTES = re.compile(r"(\d+(?:\.\d+)?)\s*MB\b")
_KILOBYTES = re.compile(r"(\d+(?:\.\d+)?)\s*KB\b")
_GIGABYTES = re.compile(r"(\d+(?:\.\d+)?)\s*GB\b")
_MILLISECONDS = re.compile(r"(\d+(?:\.\d+)?)\s*ms\b")
_SECONDS_UNIT = re.compile(r"(\d+(?:\.\d+)?)\s*s\b")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def clean_for_speech(text: str) -> str:
    """Sanitize LLM output so Piper doesn't read markdown or raw paths aloud."""
    # Code blocks — never read code aloud
    text = _CODE_BLOCK.sub("I found some code — check the terminal for details.", text)
    # Markdown formatting — strip, keep the inner text
    text = _BOLD.sub(r"\1", text)
    text = _ITALIC.sub(r"\1", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _HEADER.sub("", text)
    # File paths → just the filename
    text = _ABS_PATH.sub(r"the \1 file", text)
    text = _TILDE_PATH.sub(r"the \1 file", text)
    # Units → spoken form
    text = _MEGABYTES.sub(lambda m: f"{float(m.group(1)):g} megabytes", text)
    text = _KILOBYTES.sub(lambda m: f"{float(m.group(1)):g} kilobytes", text)
    text = _GIGABYTES.sub(lambda m: f"{float(m.group(1)):g} gigabytes", text)
    text = _MILLISECONDS.sub(lambda m: f"{float(m.group(1)):g} milliseconds", text)
    text = _SECONDS_UNIT.sub(lambda m: f"{float(m.group(1)):g} seconds", text)
    text = _PERCENT.sub(lambda m: f"{float(m.group(1)):g} percent", text)
    # Technical symbols → spoken form
    text = text.replace(" → ", " then ")
    text = text.replace(" -> ", " then ")
    text = text.replace(" <- ", ", which is ")
    text = text.replace(">=", " or more")
    text = text.replace("<=", " or less")
    # Stray backticks
    text = text.replace("`", "")
    return text.strip()


def _play_raw_pcm(raw: bytes) -> None:
    if not raw:
        return
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767.0
    sd.play(samples, samplerate=_PIPER_SAMPLE_RATE)
    sd.wait()


async def speak(text: str, config: TtsConfig) -> None:
    text = clean_for_speech(text)
    if not text:
        return
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

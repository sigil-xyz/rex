import asyncio
import logging
import threading
from typing import Any

import numpy as np
import sounddevice as sd

from rex.config import AudioConfig, VadConfig

logger = logging.getLogger(__name__)

_FRAME_DURATION = 0.02  # 20ms per callback block


class SpeechSession:
    """One armed→onset→recording→done cycle."""

    def __init__(self, audio: AudioConfig, vad: VadConfig) -> None:
        self._audio = audio
        self._vad = vad
        self._buffer: list[np.ndarray] = []
        self._last_frame: np.ndarray = np.zeros(1, dtype=np.float32)
        self._lock = threading.Lock()
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def _callback(
        self,
        indata: np.ndarray,
        _frames: int,
        _time: Any,  # CFFI CData PaStreamCallbackTimeInfo; no stub type
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            logger.warning("audio stream status: %s", status)
        arr = indata.copy()
        with self._lock:
            self._buffer.append(arr)
            self._last_frame = arr

    def _tail_rms(self) -> float:
        with self._lock:
            frame = self._last_frame
        return float(np.sqrt(np.mean(frame.flatten() ** 2)))

    def _collect(self) -> np.ndarray:
        with self._lock:
            buf = list(self._buffer)
        if not buf:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(buf, axis=0).flatten()

    async def run(self) -> np.ndarray | None:
        """Arm the mic, wait for onset, record until end-of-speech or cap.

        Returns captured audio array, or None if no speech was detected.
        """
        blocksize = int(self._audio.sample_rate * _FRAME_DURATION)
        stream = sd.InputStream(
            samplerate=self._audio.sample_rate,
            channels=self._audio.channels,
            device=self._audio.device or None,
            dtype=np.float32,
            callback=self._callback,
            blocksize=blocksize,
        )
        stream.start()
        logger.info("session armed (sr=%d, blocksize=%d)", self._audio.sample_rate, blocksize)

        try:
            # Phase 1: wait for speech onset
            onset_run = 0
            deadline_ticks = int(self._vad.onset_timeout / _FRAME_DURATION)
            for _ in range(deadline_ticks):
                if self._stop_requested:
                    logger.info("session stopped (armed, no onset)")
                    return None
                await asyncio.sleep(_FRAME_DURATION)
                if self._tail_rms() >= self._vad.onset_rms_threshold:
                    onset_run += 1
                    if onset_run >= self._vad.onset_frames:
                        logger.info("onset confirmed")
                        break
                else:
                    onset_run = 0
            else:
                logger.info("onset timeout — no speech in %.1fs", self._vad.onset_timeout)
                return None

            # Phase 2: record until silence or hard cap
            silence_run = 0
            max_ticks = int(self._vad.max_recording / _FRAME_DURATION)
            for _ in range(max_ticks):
                if self._stop_requested:
                    logger.info("session manually stopped")
                    break
                await asyncio.sleep(_FRAME_DURATION)
                if self._tail_rms() < self._vad.onset_rms_threshold:
                    silence_run += 1
                    if silence_run >= self._vad.silence_frames:
                        logger.info("end-of-speech (%d silent frames)", silence_run)
                        break
                else:
                    silence_run = 0
            else:
                logger.info("max recording reached (%.1fs)", self._vad.max_recording)

            audio = self._collect()
            logger.info(
                "captured %.2fs (%d samples)",
                len(audio) / self._audio.sample_rate,
                len(audio),
            )
            return audio

        finally:
            stream.stop()
            stream.close()

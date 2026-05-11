import logging
from typing import Any

import numpy as np
import sounddevice as sd

from rex.config import AudioConfig

logger = logging.getLogger(__name__)


class AudioRecorder:
    def __init__(self, config: AudioConfig) -> None:
        self._config = config
        self._buffer: list[np.ndarray] = []
        self._recording: bool = False
        self._stream: sd.InputStream | None = None

    def _callback(
        self,
        indata: np.ndarray,
        _frames: int,
        _time: Any,  # sounddevice passes a CFFI CData object (PaStreamCallbackTimeInfo); no stub type exists
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            logger.warning("audio stream status: %s", status)
        self._buffer.append(indata.copy())

    def start(self) -> None:
        self._recording = True
        self._buffer = []
        self._stream = sd.InputStream(
            samplerate=self._config.sample_rate,
            channels=self._config.channels,
            device=self._config.device or None,
            dtype=np.float32,
            callback=self._callback,
        )
        self._stream.start()
        logger.info(
            "recording started (sr=%d, channels=%d, device=%s)",
            self._config.sample_rate,
            self._config.channels,
            self._config.device,
        )

    def stop(self) -> np.ndarray:
        self._recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._buffer:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(self._buffer, axis=0)
        logger.info(
            "recording stopped (%d samples, %.2fs)",
            len(audio),
            len(audio) / self._config.sample_rate,
        )
        self._buffer = []
        return audio

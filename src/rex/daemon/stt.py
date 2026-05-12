import logging

import numpy as np
from faster_whisper import WhisperModel

from rex.config import SttConfig

logger = logging.getLogger(__name__)


class Transcriber:
    def __init__(self, config: SttConfig) -> None:
        self._config = config
        self._model: WhisperModel | None = None

    def load(self) -> None:
        self._model = WhisperModel(self._config.model, device=self._config.device)
        logger.info("model loaded %s and device %s", self._config.model, self._config.device)

    def transcribe(self, audio: np.ndarray) -> str:
        if self._model is None:
            raise RuntimeError("transcribe called before load(); call load() first")
        segments, _info = self._model.transcribe(audio, vad_filter=False, no_speech_threshold=1.0)
        text = " ".join(segment.text for segment in segments).strip()
        logger.debug("transcribed %s", text)
        return text

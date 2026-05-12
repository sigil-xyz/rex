import numpy as np
import pytest

from rex.config import SttConfig
from rex.daemon.stt import Transcriber


def test_transcribe_before_load_raises() -> None:
    t = Transcriber(SttConfig())
    with pytest.raises(RuntimeError, match="load()"):
        t.transcribe(np.zeros(16000, dtype=np.float32))


def test_transcribe_returns_string_after_load() -> None:
    t = Transcriber(SttConfig())
    t.load()
    result = t.transcribe(np.zeros(16000, dtype=np.float32))
    assert isinstance(result, str)


def test_transcribe_silent_audio_returns_string() -> None:
    t = Transcriber(SttConfig())
    t.load()
    audio = np.zeros(16000, dtype=np.float32)
    result = t.transcribe(audio)
    assert isinstance(result, str)

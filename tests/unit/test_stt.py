import os
import wave
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from rex.config import SttConfig
from rex.daemon.stt import Transcriber, _detect_backend, _write_wav

# Use the smallest faster-whisper model to keep tests fast
_FAST_CONFIG = SttConfig(backend="faster-whisper", model="tiny.en", device="cpu")


def test_transcribe_before_load_raises() -> None:
    t = Transcriber(_FAST_CONFIG)
    with pytest.raises(RuntimeError, match="load()"):
        t.transcribe(np.zeros(16000, dtype=np.float32))


def test_transcribe_returns_string_after_load() -> None:
    t = Transcriber(_FAST_CONFIG)
    t.load()
    result = t.transcribe(np.zeros(16000, dtype=np.float32))
    assert isinstance(result, str)


def test_transcribe_silent_audio_returns_string() -> None:
    t = Transcriber(_FAST_CONFIG)
    t.load()
    result = t.transcribe(np.zeros(16000, dtype=np.float32))
    assert isinstance(result, str)


# --- backend detection ---


def test_detect_backend_returns_valid_value() -> None:
    result = _detect_backend()
    assert result in {"parakeet", "mlx", "faster-whisper"}


def test_detect_backend_apple_silicon_with_mlx() -> None:
    with (
        patch("platform.system", return_value="Darwin"),
        patch("platform.machine", return_value="arm64"),
        patch.dict("sys.modules", {"mlx_whisper": MagicMock()}),
    ):
        assert _detect_backend() == "mlx"


def test_detect_backend_no_cuda_returns_faster_whisper() -> None:
    torch_mock = MagicMock()
    torch_mock.cuda.is_available.return_value = False
    with (
        patch("platform.system", return_value="Linux"),
        patch.dict("sys.modules", {"torch": torch_mock}),
    ):
        assert _detect_backend() == "faster-whisper"


def test_detect_backend_cuda_high_vram_with_nemo() -> None:
    props = MagicMock()
    props.total_memory = 8 * 1024**3  # 8 GB
    torch_mock = MagicMock()
    torch_mock.cuda.is_available.return_value = True
    torch_mock.cuda.get_device_properties.return_value = props
    with (
        patch("platform.system", return_value="Linux"),
        patch.dict(
            "sys.modules",
            {
                "torch": torch_mock,
                "nemo": MagicMock(),
                "nemo.collections": MagicMock(),
                "nemo.collections.asr": MagicMock(),
            },
        ),
    ):
        assert _detect_backend() == "parakeet"


def test_detect_backend_cuda_low_vram_returns_faster_whisper() -> None:
    props = MagicMock()
    props.total_memory = 4 * 1024**3  # 4 GB — below 6 GB threshold
    torch_mock = MagicMock()
    torch_mock.cuda.is_available.return_value = True
    torch_mock.cuda.get_device_properties.return_value = props
    with (
        patch("platform.system", return_value="Linux"),
        patch.dict("sys.modules", {"torch": torch_mock}),
    ):
        assert _detect_backend() == "faster-whisper"


# --- _write_wav ---


def test_write_wav_creates_valid_file() -> None:
    audio = np.random.uniform(-0.5, 0.5, 16000).astype(np.float32)
    path = _write_wav(audio)
    try:
        assert os.path.exists(path)
        with wave.open(path, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            assert wf.getnframes() == len(audio)
    finally:
        os.unlink(path)

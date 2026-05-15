import gc
import logging
import os
import platform
import tempfile
import wave
from typing import Any

import numpy as np

from rex.config import SttConfig

logger = logging.getLogger(__name__)

# All Whisper-family models and Parakeet expect 16 kHz mono float32 input
_WHISPER_SAMPLE_RATE = 16_000


def _detect_backend() -> str:
    """Return the best available STT backend for this machine."""
    # Apple Silicon — mlx-whisper uses Metal natively, no CUDA needed
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            import mlx_whisper  # noqa: F401

            logger.info("stt backend: mlx (Apple Silicon)")
            return "mlx"
        except ImportError:
            logger.warning("Apple Silicon detected but mlx-whisper not installed — falling back")

    # NVIDIA CUDA with ≥6 GB VRAM — Parakeet fits and outperforms Whisper
    try:
        import torch

        if torch.cuda.is_available():
            vram_mb: int = torch.cuda.get_device_properties(0).total_memory // (1024**2)
            if vram_mb >= 6144:
                try:
                    import nemo.collections.asr  # noqa: F401

                    logger.info("stt backend: parakeet (CUDA, %d MB VRAM)", vram_mb)
                    return "parakeet"
                except ImportError:
                    logger.warning(
                        "CUDA with %d MB VRAM available but nemo-toolkit not installed — falling back",
                        vram_mb,
                    )
    except ImportError:
        pass

    logger.info("stt backend: faster-whisper")
    return "faster-whisper"


def _write_wav(audio: np.ndarray) -> str:
    """Write float32 mono 16 kHz audio to a temp WAV file. Caller must unlink."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name

    samples = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_WHISPER_SAMPLE_RATE)
        wf.writeframes(samples.tobytes())

    return path


class Transcriber:
    def __init__(self, config: SttConfig) -> None:
        self._config = config
        self._backend: str | None = None
        # faster-whisper model (faster_whisper has no stubs; Any is intentional)
        self._fw_model: Any = None
        # NeMo EncDecRNNTBPEModel (nemo-toolkit has no stubs; Any is intentional)
        self._parakeet_model: Any = None
        # mlx-whisper loads lazily per call; only the HF repo name is stored
        self._mlx_repo: str | None = None

    def load(self) -> None:
        backend = self._config.backend
        if backend == "auto":
            backend = _detect_backend()
        self._backend = backend

        if backend == "parakeet":
            self._load_parakeet()
        elif backend == "mlx":
            self._load_mlx()
        else:
            self._load_faster_whisper()

    def _load_parakeet(self) -> None:
        import nemo.collections.asr as nemo_asr

        repo = self._config.model or "nvidia/parakeet-tdt-0.6b-v2"
        self._parakeet_model = nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(repo)
        logger.info("parakeet loaded: %s", repo)

    def _load_mlx(self) -> None:
        self._mlx_repo = self._config.model or "mlx-community/whisper-large-v3-mlx"
        logger.info("mlx-whisper ready: %s", self._mlx_repo)

    def _load_faster_whisper(self) -> None:
        from faster_whisper import WhisperModel

        model_name = self._config.model or "small.en"
        device = self._config.device or "auto"
        self._fw_model = WhisperModel(model_name, device=device, compute_type="int8")
        logger.info("faster-whisper loaded: %s on %s", model_name, device)

    def transcribe(self, audio: np.ndarray) -> str:
        if self._backend is None:
            raise RuntimeError("transcribe called before load(); call load() first")

        if self._backend == "parakeet":
            return self._transcribe_parakeet(audio)
        if self._backend == "mlx":
            return self._transcribe_mlx(audio)
        return self._transcribe_faster_whisper(audio)

    def _transcribe_parakeet(self, audio: np.ndarray) -> str:
        path = _write_wav(audio)
        try:
            output: list[str] = self._parakeet_model.transcribe([path])
            text = output[0].strip() if output else ""
        finally:
            os.unlink(path)
        logger.debug("parakeet: %s", text)
        return text

    def _transcribe_mlx(self, audio: np.ndarray) -> str:
        import mlx_whisper

        result: dict[str, str] = mlx_whisper.transcribe(audio, path_or_hf_repo=self._mlx_repo)
        text = result.get("text", "").strip()
        logger.debug("mlx: %s", text)
        return text

    def _transcribe_faster_whisper(self, audio: np.ndarray) -> str:
        segments, _info = self._fw_model.transcribe(
            audio, vad_filter=False, no_speech_threshold=1.0
        )
        text = " ".join(seg.text for seg in segments).strip()
        gc.collect()
        logger.debug("faster-whisper: %s", text)
        return text

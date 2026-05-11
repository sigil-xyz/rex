import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SttConfig:
    model: str = "tiny.en"
    device: str = "cpu"


@dataclass
class DaemonConfig:
    socket_path: str = ""
    log_level: str = "info"


@dataclass
class AudioConfig:
    sample_rate: int = 16000  # 16Khz is standard for speech
    channels: int = 1  # Mono is enough for stt
    device: str = ""


@dataclass
class TtsConfig:
    piper_bin: str = "/usr/bin/piper-tts"
    model: str = "/usr/share/piper/voices/en_US-lessac-medium.onnx"
    device: str = ""


@dataclass
class NotificationConfig:
    enabled: bool = True
    timeout: int = 5000


@dataclass
class RexConfig:
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: SttConfig = field(default_factory=SttConfig)
    tts: TtsConfig = field(default_factory=TtsConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)


def load_config(path: Path | None = None) -> RexConfig:
    if path is None:
        path = Path.home() / ".config" / "rex" / "config.toml"

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        logger.warning("config file not found at %s, using defaults", path)
        return RexConfig()

    daemon_data = data.get("daemon", {})
    daemon = DaemonConfig(
        socket_path=daemon_data.get("socket_path", DaemonConfig.socket_path),
        log_level=daemon_data.get("log_level", DaemonConfig.log_level),
    )

    audio_data = data.get("audio", {})
    audio = AudioConfig(
        sample_rate=audio_data.get("sample_rate", AudioConfig.sample_rate),
        channels=audio_data.get("channels", AudioConfig.channels),
        device=audio_data.get("device", AudioConfig.device),
    )

    stt_data = data.get("stt", {})
    stt = SttConfig(
        model=stt_data.get("model", SttConfig.model),
        device=stt_data.get("device", SttConfig.device),
    )

    tts_data = data.get("tts", {})
    tts = TtsConfig(
        piper_bin=tts_data.get("piper_bin", TtsConfig.piper_bin),
        model=tts_data.get("model", TtsConfig.model),
        device=tts_data.get("device", TtsConfig.device),
    )

    notification_data = data.get("notification", {})
    notification = NotificationConfig(
        enabled=notification_data.get("enabled", NotificationConfig.enabled),
        timeout=notification_data.get("timeout", NotificationConfig.timeout),
    )

    logger.debug("loaded config from %s", path)
    return RexConfig(
        daemon=daemon,
        audio=audio,
        stt=stt,
        tts=tts,
        notification=notification,
    )

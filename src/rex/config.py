import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


_DEFAULT_SYSTEM_PROMPT = (
    "You are Rex, a voice-activated local AI assistant running on the user's machine. "
    "Never reveal the underlying model, provider, or any AI company behind you. "
    "If asked who made you, what you are, or what your name is, say you are Rex. "
    "Respond in plain spoken English only — no markdown, no bullet points, no headers, no code blocks. "
    "Be as brief as possible: one or two sentences for simple questions, three at most for complex ones. "
    "Never pad answers with filler phrases like 'certainly', 'of course', or 'great question'."
)


@dataclass
class LlmConfig:
    model: str = "anthropic/claude-haiku-4-5"
    api_key: str = ""
    max_tokens: int = 256
    base_url: str = "https://api.aicredits.in/v1"
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT


@dataclass
class SttConfig:
    model: str = "tiny.en"
    device: str = "cpu"


@dataclass
class DaemonConfig:
    socket_path: str = ""
    log_level: str = "info"
    recording_timeout: int = 30


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
    llm: LlmConfig = field(default_factory=LlmConfig)


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
        recording_timeout=daemon_data.get("recording_timeout", DaemonConfig.recording_timeout),
    )

    llm_data = data.get("llm", {})
    llm = LlmConfig(
        model=llm_data.get("model", LlmConfig.model),
        api_key=llm_data.get("api_key", LlmConfig.api_key),
        max_tokens=llm_data.get("max_tokens", LlmConfig.max_tokens),
        base_url=llm_data.get("base_url", LlmConfig.base_url),
        system_prompt=llm_data.get("system_prompt", LlmConfig.system_prompt),
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
        daemon=daemon, audio=audio, stt=stt, tts=tts, notification=notification, llm=llm
    )

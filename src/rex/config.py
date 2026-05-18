import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)


_DEFAULT_SYSTEM_PROMPT = """\
You are Rex, a voice-operated AI assistant running locally on the user's machine.
You communicate through speech only. Follow these rules without exception.

RESPONSE STYLE:
- 2 sentences for simple questions, 3 for complex ones. Never more unless explicitly asked for detail.
- Use contractions: I'm, you've, that's, here's, it's, I'll, didn't, won't.
- Lead with the answer, not the setup.
- Never start with "Certainly", "Sure", "Of course", "Great question", "Absolutely", or any filler opener.
- Never narrate what you're about to do. Say the result.

SPEECH FORMAT:
- No markdown: no asterisks, no backticks, no hash symbols, no bullet points, no numbered lists.
- No code blocks. If you read code, describe what it does — don't recite it line by line.
- File paths: say "the pipeline file" or "the config file", not the full path.
- Numbers: round to sensible precision and say the unit — "about 40 megabytes", not "40.3 MB".
- Errors: lead with what went wrong in plain English, not a traceback.
- If asked to summarize a file, give the summary — never read it back verbatim.

TONE:
- Direct. Calm. Slightly dry. Like a colleague who knows what they're doing.
- Not enthusiastic. Not apologetic. Don't pad silence with "okay" or "so".

IDENTITY:
- You are Rex. If asked who made you, what you are, or what model you use: you are Rex, nothing more.
- Never reveal the underlying model, provider, or any AI company.

TOOLS:
- When asked to read, write, run, or search something — call the tool immediately, without announcing it.
- Never explain why something might not work before trying. Try first.\
"""


@dataclass
class LlmConfig:
    model: str = "anthropic/claude-haiku-4-5"
    api_key: str = ""
    max_tokens: int = 1024
    base_url: str = "https://api.aicredits.in/v1"
    system_prompt: str = _DEFAULT_SYSTEM_PROMPT
    memory_turns: int = 20


@dataclass
class SttConfig:
    backend: str = "auto"  # "auto" | "parakeet" | "mlx" | "faster-whisper"
    model: str = ""  # empty = backend picks its own default
    device: str = "cpu"  # used by faster-whisper only


@dataclass
class DaemonConfig:
    socket_path: str = ""
    log_level: str = "info"
    recording_timeout: int = 10


@dataclass
class VadConfig:
    onset_rms_threshold: float = 0.01  # RMS energy floor per 20ms frame to count as speech
    onset_frames: int = 5              # consecutive speech frames required to confirm onset
    silence_frames: int = 30           # consecutive silence frames to trigger end-of-speech
    onset_timeout: float = 8.0         # seconds to wait for onset before discarding
    max_recording: float = 10.0        # hard cap on recording duration after onset


@dataclass
class AudioConfig:
    sample_rate: int = 16000  # 16Khz is standard for speech
    channels: int = 1  # Mono is enough for stt
    device: str = ""


@dataclass
class TtsConfig:
    piper_bin: str = "piper-tts"  # resolved via PATH; override if not in PATH
    model: str = "/usr/share/piper/voices/en_US-lessac-medium.onnx"
    device: str = ""


@dataclass
class NotificationConfig:
    enabled: bool = True
    timeout: int = 5000


@dataclass
class ToolsConfig:
    enabled: bool = True
    confirmation_timeout: int = 30


@dataclass
class OutputConfig:
    mode: str = "auto"  # "auto" | "voice" | "text" | "notify-only"


@dataclass
class MemoryConfig:
    recent_tool_calls: int = 5
    project_context_path: str = ""


def resolve_output_mode(config_mode: str, input_was_voice: bool) -> Literal["voice", "text"]:
    if config_mode == "voice":
        return "voice"
    if config_mode == "text":
        return "text"
    if config_mode == "notify-only":
        return "text"
    # auto
    return "voice" if input_was_voice else "text"


@dataclass
class RexConfig:
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: SttConfig = field(default_factory=SttConfig)
    tts: TtsConfig = field(default_factory=TtsConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    llm: LlmConfig = field(default_factory=LlmConfig)
    tools: ToolsConfig = field(default_factory=ToolsConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    vad: VadConfig = field(default_factory=VadConfig)
    memory_db: str = ""  # empty = use DEFAULT_DB_PATH


def resolve_socket_path(override: str = "") -> Path:
    """Return the Unix socket path, honoring daemon.socket_path if configured."""
    if override:
        return Path(override).expanduser()
    import os

    runtime_dir = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return Path(runtime_dir) / "rex.sock"


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
        memory_turns=llm_data.get("memory_turns", LlmConfig.memory_turns),
    )

    audio_data = data.get("audio", {})
    audio = AudioConfig(
        sample_rate=audio_data.get("sample_rate", AudioConfig.sample_rate),
        channels=audio_data.get("channels", AudioConfig.channels),
        device=audio_data.get("device", AudioConfig.device),
    )

    stt_data = data.get("stt", {})
    stt = SttConfig(
        backend=stt_data.get("backend", SttConfig.backend),
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

    tools_data = data.get("tools", {})
    tools = ToolsConfig(
        enabled=tools_data.get("enabled", ToolsConfig.enabled),
        confirmation_timeout=tools_data.get(
            "confirmation_timeout", ToolsConfig.confirmation_timeout
        ),
    )

    output_data = data.get("output", {})
    output = OutputConfig(
        mode=output_data.get("mode", OutputConfig.mode),
    )

    memory_data = data.get("memory", {})
    memory = MemoryConfig(
        recent_tool_calls=memory_data.get("recent_tool_calls", MemoryConfig.recent_tool_calls),
        project_context_path=memory_data.get(
            "project_context_path", MemoryConfig.project_context_path
        ),
    )

    vad_data = data.get("vad", {})
    vad = VadConfig(
        onset_rms_threshold=vad_data.get("onset_rms_threshold", VadConfig.onset_rms_threshold),
        onset_frames=vad_data.get("onset_frames", VadConfig.onset_frames),
        silence_frames=vad_data.get("silence_frames", VadConfig.silence_frames),
        onset_timeout=vad_data.get("onset_timeout", VadConfig.onset_timeout),
        max_recording=vad_data.get("max_recording", VadConfig.max_recording),
    )

    logger.debug("loaded config from %s", path)
    return RexConfig(
        daemon=daemon,
        audio=audio,
        stt=stt,
        tts=tts,
        notification=notification,
        llm=llm,
        tools=tools,
        output=output,
        memory=memory,
        vad=vad,
        memory_db=data.get("memory_db", ""),
    )

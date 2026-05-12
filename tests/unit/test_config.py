from pathlib import Path

from rex.config import (
    AudioConfig,
    DaemonConfig,
    NotificationConfig,
    RexConfig,
    SttConfig,
    TtsConfig,
    load_config,
)


def test_load_config_missing_file(tmp_path: Path) -> None:
    config = load_config(tmp_path / "nonexistent.toml")
    assert isinstance(config, RexConfig)
    assert config.stt.model == ""
    assert config.stt.backend == "auto"
    assert config.daemon.log_level == "info"


def test_load_config_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text("")
    config = load_config(p)
    assert config.stt.model == ""
    assert config.stt.backend == "auto"
    assert config.audio.sample_rate == 16000


def test_load_config_partial(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text('[stt]\nmodel = "base.en"\n')
    config = load_config(p)
    assert config.stt.model == "base.en"
    assert config.stt.device == "cpu"
    assert config.audio.sample_rate == 16000


def test_load_config_full(tmp_path: Path) -> None:
    p = tmp_path / "config.toml"
    p.write_text(
        "[daemon]\nlog_level = 'debug'\n"
        "[audio]\nsample_rate = 22050\n"
        "[stt]\nmodel = 'small.en'\ndevice = 'cuda'\n"
        "[tts]\npiper_bin = '/usr/local/bin/piper-tts'\n"
        "[notification]\nenabled = false\ntimeout = 3000\n"
    )
    config = load_config(p)
    assert config.daemon.log_level == "debug"
    assert config.audio.sample_rate == 22050
    assert config.stt.model == "small.en"
    assert config.stt.device == "cuda"
    assert config.tts.piper_bin == "/usr/local/bin/piper-tts"
    assert config.notification.enabled is False
    assert config.notification.timeout == 3000


def test_defaults() -> None:
    c = RexConfig()
    assert c.daemon == DaemonConfig()
    assert c.audio == AudioConfig()
    assert c.stt == SttConfig()
    assert c.tts == TtsConfig()
    assert c.notification == NotificationConfig()

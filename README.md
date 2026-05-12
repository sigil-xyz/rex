<div align="center">

# Rex

**A local AI assistant daemon for Linux and macOS.**

[![CI](https://github.com/sigil-xyz/rex/actions/workflows/ci.yml/badge.svg)](https://github.com/sigil-xyz/rex/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org)
[![License: GPL v3](https://img.shields.io/badge/license-GPL%20v3-blue)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos-lightgrey)](#installation)

</div>

---

Rex is a background daemon that listens for a configurable hotkey, records your voice, and responds — spoken aloud and as a desktop notification. Everything runs locally. No cloud. No telemetry.

> **Status:** Active development. See the [roadmap](docs/roadmap.md).

---

## Highlights

- **On-device speech recognition** — auto-selects the best available STT backend:
  [Parakeet TDT](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) (NVIDIA ≥6 GB VRAM),
  [mlx-whisper](https://github.com/ml-explore/mlx-examples) (Apple Silicon), or
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (universal fallback)
- **Natural voice output** — [Piper TTS](https://github.com/rhasspy/piper) synthesizes responses
  with low latency; playback via sounddevice on both Linux and macOS
- **Configurable trigger** — bind any hotkey via your compositor, window manager, or skhd
- **Desktop notifications** — `notify-send` on Linux, `osascript` on macOS; no extra deps
- **Offline by default** — the core voice loop has no network dependency
- **Low idle footprint** — the daemon idles at under 30 MB; models load on first use
- **systemd / launchd native** — starts on login, integrates with the graphical session

---

## Installation

```bash
git clone https://github.com/sigil-xyz/rex
cd rex
bash scripts/setup.sh
```

The setup script detects your hardware, installs the right STT backend, downloads Piper and a
voice model, and writes `~/.config/rex/config.toml`.

For manual installation or troubleshooting, see [docs/installation.md](docs/installation.md).

---

## Quickstart

**1. Configure**

```bash
cp config/config.example.toml ~/.config/rex/config.toml
```

Edit `~/.config/rex/config.toml` — at minimum, set `tts.model` to the path of your downloaded voice model.

**2. Start the daemon**

```bash
just service-install
```

Or run in the foreground to see what's happening:

```bash
just dev
```

**3. Bind a hotkey**

Rex responds to a `start` and `stop` signal sent via `rex-trigger`. Bind these to any key in your compositor, window manager, or system hotkey daemon.

Example for **Hyprland**:

```ini
# ~/.config/hypr/hyprland.conf
bind = SUPER, Space, exec, rex-trigger start
bindrelease = SUPER, Space, exec, rex-trigger stop
```

**4. Speak**

Hold the hotkey, say something, release. Rex responds with voice and a desktop notification.

For detailed setup instructions per platform, see [docs/installation.md](docs/installation.md).

---

## Platform Support

| Platform | Status |
|----------|--------|
| Arch Linux (Wayland / Hyprland) | Primary target |
| Linux (X11 / other compositors) | Supported |
| macOS | Supported |
| Windows | Not planned |

---

## Documentation

| Document | Description |
|----------|-------------|
| [Installation](docs/installation.md) | Full setup guide per platform |
| [Configuration](docs/configuration.md) | All config keys with defaults |
| [Architecture](docs/architecture.md) | How Rex works internally |
| [Roadmap](docs/roadmap.md) | What's planned and what's not |

---

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and [HACKING.md](HACKING.md) for internals. All contributions require passing CI. Security issues go to [SECURITY.md](SECURITY.md).

---

## License

Rex is free software: you can redistribute it and/or modify it under the terms of the [GNU General Public License v3.0](LICENSE).

© 2026 [sigil-xyz](https://github.com/sigil-xyz)

<div align="center">

<br />

```
██████╗ ███████╗██╗  ██╗
██╔══██╗██╔════╝╚██╗██╔╝
██████╔╝█████╗   ╚███╔╝
██╔══██╗██╔══╝   ██╔██╗
██║  ██║███████╗██╔╝ ██╗
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
```

**Your personal AI assistant. Local. Private. Always there.**

_Not a chatbot. Not a voice toy. Infrastructure that thinks alongside you._

<br />

[![CI](https://github.com/sigil-xyz/rex/actions/workflows/ci.yml/badge.svg)](https://github.com/sigil-xyz/rex/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)](https://www.python.org)
[![License: GPL v3](https://img.shields.io/badge/license-GPL%20v3-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos-lightgrey?style=flat-square)](#installation)
[![Status](https://img.shields.io/badge/status-early%20development-orange?style=flat-square)](#status)

<br />

</div>

---

> **Rex is in early development.** The core loop works — voice in, LLM, tools, voice out. But rough edges exist. Early adopters will hit them. If you do, [open an issue](https://github.com/sigil-xyz/rex/issues) — that's how Rex gets better.

---

## What Rex Is

Rex is a daemon. It runs silently in the background and waits for you.

Speak to it. Type to it. Script it. It doesn't care how input arrives. It cares about understanding you, remembering what you're working on, and taking real action — reading files, running commands, searching the web — not just producing text you have to act on yourself.

Everything stays on your machine. No cloud. No telemetry. No account. No company sees what you ask or what Rex does.

The long-term vision is simple: **assistant for everyone** — any user, any hardware, any field. Rex today is the honest first step toward that. Linux and macOS, voice and text, local tools, project memory. A foundation, not a finished product.

---

## What Rex Is Not

- **Not a chatbot** — Rex takes actions, not just answers
- **Not always listening** — push-to-talk only, never ambient
- **Not a cloud product** — everything runs on your hardware
- **Not finished** — early development, expect rough edges

---

## How It Works

```
You speak or type
       │
       ▼
  Rex transcribes                 ← on-device, nothing leaves your machine
       │
       ▼
  LLM reasons + plans             ← any OpenAI-compatible endpoint
       │
       ├──► reads a file
       ├──► runs a shell command   ← with your confirmation
       ├──► searches the web
       └──► speaks + notifies      ← Piper TTS, local notification
```

One daemon. One asyncio process. Under 30 MB idle. Starts on login.

---

## Features

**Input**

- Push-to-talk via any hotkey (compositor, skhd, Karabiner)
- _(coming soon)_ `rex ask "..."` — one-shot text query
- _(coming soon)_ `rex chat` — persistent terminal session

**Speech Recognition — auto-selects best available**

- [Parakeet TDT 0.6B](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) on NVIDIA ≥ 6 GB VRAM
- [mlx-whisper](https://github.com/ml-explore/mlx-examples) on Apple Silicon
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) everywhere else

**Tools Rex Can Use**

- `read_file` — reads any file you point it to
- `write_file` — writes files, always asks for confirmation first
- `shell` — runs shell commands, always asks for confirmation first
- `clipboard` — reads and writes your clipboard
- `web_search` — searches via ddgr, no API key needed

**Memory**

- Conversation history persists across sessions (SQLite, local)
- _(coming soon)_ Project context — Rex remembers what you're building

**Output**

- Voice response via [Piper TTS](https://github.com/rhasspy/piper) — local, fast, no cloud
- Desktop notification alongside every response
- _(coming soon)_ Text-only mode for when voice isn't appropriate

---

## Installation

> **Requirements:** Python 3.11+, `uv`, PortAudio, and either Arch Linux or macOS.
> Debian/Ubuntu works but setup is more manual — see [docs/installation.md](docs/installation.md).

```bash
git clone https://github.com/sigil-xyz/rex
cd rex
bash scripts/setup.sh
```

The setup script handles everything:

- Detects your hardware (NVIDIA / Apple Silicon / CPU)
- Installs the right STT backend
- Downloads Piper and a voice model
- Writes `~/.config/rex/config.toml`

---

## Quickstart

**1. Add your API key**

Rex uses any OpenAI-compatible endpoint. By default it routes to Claude Haiku via [aicredits.in](https://aicredits.in), but you can point it at OpenAI, a local Ollama instance, or anything else.

```toml
# ~/.config/rex/config.toml
[llm]
api_key   = "your-api-key"
base_url  = "https://api.aicredits.in/v1"   # or any OpenAI-compatible URL
model     = "anthropic/claude-haiku-4-5"
```

**2. Start the daemon**

```bash
# Linux — setup.sh installs the systemd service automatically
systemctl --user status rex

# macOS — run manually for now (launchd automation coming soon)
rex
```

**3. Bind a hotkey**

```ini
# Hyprland (~/.config/hypr/hyprland.conf)
bind        = SUPER, Space, exec, rex-trigger start
bindrelease = SUPER, Space, exec, rex-trigger stop
```

For other compositors, X11, skhd, and Karabiner — see [docs/installation.md](docs/installation.md).

**4. Hold the hotkey, speak, release.**

Rex transcribes, thinks, acts, responds. That's the loop.

---

## Platform Support

| Platform                        | Status                                        |
| ------------------------------- | --------------------------------------------- |
| Arch Linux — Wayland / Hyprland | ✅ Primary target                             |
| Linux — X11 / other compositors | ✅ Supported                                  |
| macOS                           | ✅ Supported (launchd automation in progress) |
| Windows                         | ✗ Not planned                                 |

---

## Status

Rex is in **early development**. The table below reflects what actually works right now.

| Capability                          | Status        |
| ----------------------------------- | ------------- |
| Push-to-talk voice input            | ✅ Working    |
| On-device STT (3 backends)          | ✅ Working    |
| LLM integration (streaming)         | ✅ Working    |
| Piper TTS voice output              | ✅ Working    |
| Tools (file, shell, web, clipboard) | ✅ Working    |
| Conversation memory (SQLite)        | ✅ Working    |
| Text input mode                     | 🔄 In roadmap |
| Project memory / goal tracking      | 🔄 In roadmap |
| Project scaffolding                 | 🔄 In roadmap |
| First-run wizard                    | 🔄 In roadmap |
| AUR / Homebrew package              | 🔄 In roadmap |

The core is solid. What's missing is depth, polish, and breadth. That's what the roadmap addresses.

---

## Documentation

|                                        |                                |
| -------------------------------------- | ------------------------------ |
| [Installation](docs/installation.md)   | Full setup per platform        |
| [Configuration](docs/configuration.md) | Every config key with defaults |
| [Architecture](docs/architecture.md)   | How Rex works internally       |
| [Roadmap](docs/roadmap.md)             | Where Rex is going             |
| [IDEA.md](IDEA.md)                     | The long-term vision           |

---

## Contributing

Rex is open source and contributions are welcome at every level — bug reports, docs, new tools, STT backend improvements, anything.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and [HACKING.md](HACKING.md) for internals. All contributions require passing CI.

A few things worth knowing before you dive in:

- Rex is intentionally minimal. Features that belong in a plugin shouldn't be in core.
- The daemon is single-process asyncio. No threads unless absolutely necessary.
- Privacy is non-negotiable. Nothing that adds cloud dependency touches main.
- Read [IDEA.md](IDEA.md) first — understanding the vision prevents building in the wrong direction.

Security issues → [SECURITY.md](SECURITY.md)

---

## Why Rex

There are many AI assistants. Most are cloud products. Most require an account. Most are voice-first or chat-first. Most forget you between sessions.

Rex is built on a different assumption: **your assistant should live on your machine, know your work, and stay out of your way until you need it.** Input method shouldn't matter. Privacy shouldn't be a premium feature. Memory shouldn't reset on restart.

That's the idea. Rex is the early, honest version of it.

---

<div align="center">

<br />

**[Roadmap](docs/roadmap.md) · [Issues](https://github.com/sigil-xyz/rex/issues) · [IDEA.md](IDEA.md)**

<br />

Rex is free software — [GPL v3.0](LICENSE)

© 2026 [sigil-xyz](https://github.com/sigil-xyz)

</div>

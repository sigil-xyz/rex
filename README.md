<div align="center">

```
██████╗ ███████╗██╗  ██╗
██╔══██╗██╔════╝╚██╗██╔╝
██████╔╝█████╗   ╚███╔╝
██╔══██╗██╔══╝   ██╔██╗
██║  ██║███████╗██╔╝ ██╗
╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
```

**local · private · yours**

_Not a chatbot. Not a voice toy. Infrastructure that thinks alongside you._

<br/>

[![CI](https://github.com/sigil-xyz/rex/actions/workflows/ci.yml/badge.svg)](https://github.com/sigil-xyz/rex/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square)](https://www.python.org)
[![License: GPL v3](https://img.shields.io/badge/license-GPL%20v3-blue?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos-lightgrey?style=flat-square)](#installation)
[![Status](https://img.shields.io/badge/status-early%20development-orange?style=flat-square)](#status)

</div>

---

> **Early development.** The core loop works — speak or type, LLM reasons, tools act, Rex responds. Rough edges exist and early adopters will find them. When you do, [open an issue](https://github.com/sigil-xyz/rex/issues) — that's how Rex gets better.

---

## What Rex Is

Rex is a daemon. It runs in the background, waits for you, and acts when you call it.

Speak to it. Type to it. Script it. It doesn't care how input arrives — it cares about understanding you, remembering what you're working on, and taking real action. Reading files. Running commands. Searching the web. Not producing text you have to act on yourself.

Everything stays on your machine. No cloud. No telemetry. No account. No company sees what you ask or what Rex does.

The long-term vision: **a JARVIS for everyone** — any user, any hardware, any field. Rex today is the honest first step. Linux and macOS, voice and text, local tools, project memory. A foundation, not a finished product.

---

## What Rex Is Not

- **Not a chatbot** — Rex takes actions, not just answers
- **Not always listening** — push-to-talk only, never ambient
- **Not a cloud product** — everything runs on your hardware
- **Not finished** — early development, expect rough edges

---

## How It Works

```
you speak or type
        │
        ▼
  transcribes on-device        ← nothing leaves your machine
        │
        ▼
  LLM reasons and plans        ← any OpenAI-compatible endpoint
        │
        ├──► reads a file
        ├──► runs a shell command    ← with your confirmation
        ├──► searches the web
        └──► speaks + notifies       ← Piper TTS, local notification
```

One daemon. One asyncio process. Under 30 MB idle. Starts on login.

---

## Features

**Input**

- Push-to-talk via any hotkey (compositor, skhd, Karabiner)
- `rex-ask "..."` — one-shot text query, no daemon needed
- `rex-chat` — persistent terminal session, shares memory with voice daemon

**Speech recognition** — auto-selects the best available backend

- [Parakeet TDT 0.6B](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) on NVIDIA ≥ 6 GB VRAM
- [mlx-whisper](https://github.com/ml-explore/mlx-examples) on Apple Silicon
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) everywhere else

**Tools**

- `read_file` — reads any file you point it to
- `write_file` — writes files, always asks for confirmation first
- `shell` — runs shell commands, always asks for confirmation first
- `clipboard` — reads and writes your clipboard
- `web_search` — searches via ddgr, no API key needed

**Memory**

- Conversation history persists across sessions (SQLite, local)
- _(coming in v0.4)_ Project context — Rex remembers what you're building

**Output**

- Voice via [Piper TTS](https://github.com/rhasspy/piper) — local, fast, no cloud
- Desktop notification alongside every response
- Text mode — input determines output, no forced voice

---

## Installation

> **Requirements:** Python 3.11+, `uv`, PortAudio. Primary targets are Arch Linux and macOS.
> Debian/Ubuntu works but setup is more manual — see [docs/installation.md](docs/installation.md).

```bash
git clone https://github.com/sigil-xyz/rex
cd rex
bash scripts/setup.sh
```

The setup script handles everything — detects your hardware, installs the right STT backend,
downloads Piper and a voice model, writes `~/.config/rex/config.toml`.

---

## Quickstart

**1. Add your API key**

Rex works with any OpenAI-compatible endpoint. By default it routes to Claude Haiku
via [aicredits.in](https://aicredits.in), but OpenAI, local Ollama, or anything else works.

```toml
# ~/.config/rex/config.toml
[llm]
api_key  = "your-api-key"
base_url = "https://api.aicredits.in/v1"
model    = "anthropic/claude-haiku-4-5"
```

**2. Start the daemon**

```bash
# Linux — setup.sh installs the systemd service automatically
systemctl --user status rex

# macOS — run manually for now (launchd automation coming in v0.8)
rex
```

**3. Bind a hotkey**

```ini
# Hyprland (~/.config/hypr/hyprland.conf)
bind        = SUPER, Space, exec, rex-trigger start
bindrelease = SUPER, Space, exec, rex-trigger stop
```

For X11, skhd, and Karabiner — see [docs/installation.md](docs/installation.md).

**4. Hold the hotkey, speak, release — or just type:**

```bash
rex-ask "what files changed in the last commit"
rex-chat
```

Rex transcribes, thinks, acts, responds. That's the loop.

---

## Platform Support

| Platform                        | Status                                          |
| ------------------------------- | ----------------------------------------------- |
| Arch Linux — Wayland / Hyprland | ✅ Primary target                               |
| Linux — X11 / other compositors | ✅ Supported                                    |
| macOS                           | ✅ Supported _(launchd automation in progress)_ |
| Windows                         | ✗ Not planned                                   |

---

## Status

Rex is in **early development**. This table reflects what actually works right now.

| Capability                                | Status     |
| ----------------------------------------- | ---------- |
| Push-to-talk voice input                  | ✅ Working |
| On-device STT — 3 backends, auto-selected | ✅ Working |
| LLM integration — streaming, tool calling | ✅ Working |
| Piper TTS voice output                    | ✅ Working |
| Tools — file, shell, web, clipboard       | ✅ Working |
| Conversation memory — SQLite, local       | ✅ Working |
| Text input — `rex ask` / `rex chat`       | ✅ Working |
| Project memory and goal tracking          | 🔜 v0.4    |
| First-run wizard                          | 🔜 v0.5    |
| Project scaffolding                       | 🔜 v0.6    |
| Context awareness — editor, git, window   | 🔜 v0.7    |
| AUR / Homebrew package                    | 🔜 v1.0    |

The core is solid. What's missing is depth, polish, and reach. That's the roadmap.

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

Contributions are welcome at every level — bug reports, docs, new tools, STT backends, anything.

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and [HACKING.md](HACKING.md) for internals.
All contributions require passing CI. A few things worth knowing before you start:

- Rex is intentionally minimal. Features that belong in a plugin shouldn't be in core.
- The daemon is single-process asyncio. No threads unless absolutely necessary.
- Privacy is non-negotiable. Nothing that adds a cloud dependency touches `main`.
- Read [IDEA.md](IDEA.md) first — understanding the vision prevents building in the wrong direction.

Security issues → [SECURITY.md](SECURITY.md)

---

## Why Rex

Most AI assistants are cloud products. Most require an account. Most forget you between sessions.
Most force you into one input method.

Rex is built on a different assumption: **your assistant should live on your machine, know your
work, and stay out of your way until you need it.** Input method shouldn't matter. Privacy
shouldn't be a premium feature. Memory shouldn't reset on restart.

That's the idea. Rex is the early, honest version of it.

---

<div align="center">

[Roadmap](docs/roadmap.md) · [Issues](https://github.com/sigil-xyz/rex/issues) · [IDEA.md](IDEA.md)

<br/>

Rex is free software — [GPL v3.0](LICENSE) · © 2026 [sigil-xyz](https://github.com/sigil-xyz)

</div>

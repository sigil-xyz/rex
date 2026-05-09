# Rex — Project Context

## What This Is

Rex is a voice-activated local AI assistant daemon for Arch Linux. It runs as a systemd user service. Users interact via a push-to-talk hotkey (Hyprland), speak a query, and get a voice response (Piper TTS) plus a desktop notification.

## Current State

v0.0.1 — project scaffolding complete, no code written yet. Core loop being implemented: hotkey → STT → offline response engine → TTS + notification.

## Tech Stack

- Python 3.11+, asyncio, no threading
- faster-whisper (STT, runs in-process)
- Piper TTS (subprocess)
- sounddevice + numpy (audio)
- Unix socket IPC
- systemd user service
- uv (package manager)
- ruff + mypy + pytest (toolchain)

## Key Constraints

- Daemon idle RAM target: <30MB (Whisper model loaded separately, ~150MB)
- No threading — asyncio only
- Piper via subprocess, not Python bindings (stability)
- No temp audio files — pass numpy array directly to Whisper
- Config at `~/.config/rex/config.toml`
- Socket at `$XDG_RUNTIME_DIR/rex.sock`

## Non-Goals for v0.0.1

- Claude API (v0.1)
- Persistent memory (v0.1)
- Tool use (v0.2)
- Security monitoring (v0.4)

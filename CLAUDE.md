# Rex — Claude Code Instructions

## Project

Rex is a voice-activated local AI assistant daemon for Arch Linux / Hyprland. It runs as a systemd user service. The core loop: push-to-talk hotkey → STT (faster-whisper) → response engine → TTS (Piper) + desktop notification.

## Key Files

- `src/rex/daemon/main.py` — asyncio daemon, unix socket server
- `src/rex/daemon/audio.py` — sounddevice recording
- `src/rex/daemon/stt.py` — faster-whisper wrapper
- `src/rex/daemon/llm.py` — response engine
- `src/rex/daemon/tts.py` — Piper TTS subprocess
- `src/rex/cli/trigger.py` — hotkey CLI
- `src/rex/config.py` — config.toml parsing
- `HACKING.md` — internals, design decisions
- `STYLE.md` — code conventions

## Standards

- All checks: `just check`
- No `Any` without explanation
- Asyncio only — no threading
- Subprocess for Piper (not bindings)
- Unix socket at `$XDG_RUNTIME_DIR/rex.sock`

## Do Not

- Commit directly to `main`
- Add dependencies without justification in the PR
- Skip type annotations on public functions
- Break the asyncio event loop with blocking calls

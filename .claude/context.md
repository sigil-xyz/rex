# Rex — Project Context

## What This Is

Rex is a voice-activated local AI assistant daemon for Linux and macOS, inspired by JARVIS.
It runs as a systemd user service. Users interact via push-to-talk (Hyprland hotkey), speak a
query, and get a voice response (Piper TTS) plus a desktop notification.

Full vision: `IDEA.md`. Roadmap: `docs/roadmap.md`.

## Current Version: v0.3.0

**What works:**
- Push-to-talk → STT → LLM (streaming) → TTS (sentence-by-sentence) → desktop notification
- Three STT backends auto-selected: Parakeet (NVIDIA ≥6GB), mlx-whisper (Apple Silicon),
  faster-whisper (universal fallback)
- Six tools: `read_file`, `write_file`, `shell`, `clipboard_read`, `clipboard_write`, `web_search`
- Tool trust gate: read-trust runs silently; write/execute requires verbal PTT confirmation
- Persistent conversation memory (SQLite, last N turns injected into LLM context)
- Tool calls persisted to `tool_calls` table (not yet injected into LLM context — v0.4)
- `rex-ask "question"` — one-shot query from terminal, no daemon required
- `rex-chat` — persistent REPL, shares memory with voice daemon
- `[output]` config section — `mode = "auto"` resolves to text for CLI, voice for PTT

**Next milestone: v0.4 — Project Memory & Goals**

## Tech Stack

- Python 3.11+, asyncio only — no threads
- faster-whisper (STT fallback, runs in-process)
- Piper TTS (subprocess — crash isolation)
- sounddevice + numpy (audio I/O)
- openai SDK against OpenAI-compatible endpoint
- SQLite (conversation memory + tool call history)
- Unix socket IPC at `$XDG_RUNTIME_DIR/rex.sock`
- systemd user service (Linux), manual/launchd (macOS)
- uv, ruff, mypy strict, pytest

## Source Layout

```
src/rex/
├── config.py          — config.toml parsing, dataclasses, resolve_socket_path(), resolve_output_mode()
├── daemon/
│   ├── main.py        — asyncio event loop, socket server, PTT confirmation state machine
│   ├── pipeline.py    — shared LLM+tool pipeline: run_query() used by daemon and CLI
│   ├── audio.py       — sounddevice recording
│   ├── stt.py         — Transcriber: backend detection + all three backends
│   ├── llm.py         — AsyncOpenAI streaming client, ToolCallRequest
│   ├── tts.py         — Piper subprocess + sounddevice playback
│   ├── tools.py       — REGISTRY, ToolDef, trust levels, 6 tool implementations
│   └── memory.py      — SQLite: turns + tool_calls tables
└── cli/
    ├── trigger.py     — one-shot socket client (start/stop)
    └── ask.py         — rex-ask (one-shot query) and rex-chat (REPL); no daemon required
```

## Key Constraints

- No threads — asyncio only. CPU-bound work via `loop.run_in_executor`.
- Piper via subprocess, not Python bindings (stability — crash isolation).
- Audio as `numpy.ndarray` (float32, 16 kHz mono) passed directly to STT.
- Single LLM call per query — tool results formatted locally, no second round-trip.
- Config at `~/.config/rex/config.toml`. Parsed once at startup.
- Socket at `$XDG_RUNTIME_DIR/rex.sock` (or `daemon.socket_path` if configured).

## Rules

- No mention of AI tools in commit messages, code comments, docstrings, or PR descriptions.
- No threading — asyncio only.
- No `Any` without an inline comment.
- Type annotations required on all public functions.
- Tests required for all non-trivial logic.
- 80% coverage minimum (enforced by CI).

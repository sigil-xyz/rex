# Changelog

All notable changes to Rex are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.3.0] - 2026-05-16

### Added

- `rex-ask <question>` — one-shot text query from the terminal, no daemon required
- `rex-chat` — persistent REPL that shares conversation memory with the voice daemon
- `pipeline.py` — shared LLM+tool pipeline used by both the voice daemon and CLI commands
- `OutputConfig` and `resolve_output_mode()` — new `[output]` config section with `auto/voice/text/notify-only` modes
- `format_tool_error()` — actionable install hints when `ddgr` or `wl-clipboard` are missing
- Write/execute tools in text mode prompt `[y/N]:` via stdin; read tools run silently

### Changed

- `RexDaemon._on_query` refactored to delegate to `pipeline.run_query` — voice path behaviour unchanged

## [0.2.0] - 2026-05-16

### Added

- Tool use with a per-tool trust model (`read` / `write` / `execute`)
- `read_file` — reads any file within the home directory
- `write_file` — writes files, always requires verbal confirmation first
- `shell` — runs shell commands with a blocklist and verbal confirmation gate
- `web_search` — DuckDuckGo search via `ddgr`, no API key required
- `clipboard_read` / `clipboard_write` — Wayland clipboard via `wl-paste` / `wl-copy`
- Confirmation state machine: PTT press cancels a pending confirmation timeout
- Tool calls persisted to SQLite `tool_calls` table, linked to conversation turn
- Three STT backends — Parakeet TDT 0.6B v2 (NVIDIA ≥6 GB), mlx-whisper (Apple Silicon),
  faster-whisper (universal fallback) — auto-selected at startup
- macOS notification support via `osascript`

## [0.1.0] - 2026-05-09

### Added

- LLM integration via OpenAI-compatible API (Claude Haiku by default)
- Persistent conversation memory — SQLite, configurable turn window (`memory_turns`)
- Streaming TTS — Rex speaks sentence by sentence while the LLM is still generating
- Config management via `~/.config/rex/config.toml` with full section support

## [0.0.1] - 2026-05-09

### Added

- Core voice loop: push-to-talk hotkey → STT → response → TTS
- Hyprland integration via `bind`/`bindrelease` for push-to-talk
- On-device STT using `faster-whisper` with `tiny.en` model
- Voice output via Piper TTS (`en_US-lessac-medium`)
- Desktop notification output via `notify-send`
- Keyword-based offline response engine (no API required)
- systemd user service (`rex.service`)
- Unix socket IPC at `$XDG_RUNTIME_DIR/rex.sock`
- `rex-trigger` CLI for hotkey integration

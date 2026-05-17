# Changelog

All notable changes to Rex are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.5.0] - 2026-05-16

### Added

- `rex-indicator` — GTK4 + gtk4-layer-shell floating pill overlay for Wayland compositors
  - States: `listening` (red dot), `thinking` (spinner), `done` (green, auto-dismisses 1.5 s),
    `error` (amber, auto-dismisses 3 s)
  - Tokyo Night colour palette, anchored top-centre, input passthrough via empty cairo region
  - Unix socket IPC at `$XDG_RUNTIME_DIR/rex-indicator.sock`; auto-starts on first `show` command
  - `async_show()` / `async_hide()` helpers used by the voice daemon (fire-and-forget)
- `tts.clean_for_speech()` — preprocessing layer that runs before every Piper call:
  strips markdown formatting, replaces code blocks with a spoken alternative, rewrites
  absolute paths to filenames, converts unit abbreviations (MB/KB/ms/%) to spoken form,
  replaces symbols (`→`, `>=`) with words
- Rewritten system prompt tuned for conversational voice output: 2–3 sentence limit,
  contractions required, no markdown, paths humanised, direct/dry tone

### Changed

- `tts.speak()` now runs `clean_for_speech()` on every string before sending to Piper;
  empty strings after cleaning are silently skipped

### Fixed

- `rex-indicator` daemon re-execs itself with `LD_PRELOAD=libgtk4-layer-shell.so.0` when
  the library was not pre-linked before libwayland-client (upstream layer-shell requirement)
- Replaced non-existent `Gtk4LayerShell.auto_exclusive_zone_disable()` with
  `set_exclusive_zone(window, 0)` — correct API in gtk4-layer-shell 1.x

## [0.4.0] - 2026-05-16

### Added

- `facts` table in `memory.db` — persistent user facts that survive restarts
- `rex-remember` CLI — save, list, and forget facts by index
  (`rex-remember "I use neovim"`, `rex-remember --list`, `rex-remember --forget 2`)
- `MemoryConfig` — new `[memory]` config section with `recent_tool_calls` and
  `project_context_path` keys
- `_load_project_context()` — reads `.rex/context.md` from the current working directory
  (or an explicit path via config) and injects it into every LLM prompt
- `build_messages()` accepts `facts`, `recent_tool_calls`, and `project_context`;
  assembles them into the system message and a tool-history injection block
- Recent tool call history (name, args, result, status) injected into LLM context
  so Rex knows what it did in previous turns

### Changed

- `save_fact()` returns `bool` — `True` on insert, `False` on duplicate (idempotent)
- `run_query()` accepts `cwd: Path | None`; `rex-ask` and `rex-chat` pass `Path.cwd()`
  so project context auto-loads from the working directory

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

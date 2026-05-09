# Changelog

All notable changes to Rex are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

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

# Status

Current version: **v0.5.0**

---

## What works

| Component | Status | Notes |
|-----------|--------|-------|
| Hotkey push-to-talk | Working | Hyprland `bind`/`bindrelease`, any compositor |
| Unix socket IPC | Working | `$XDG_RUNTIME_DIR/rex.sock` |
| Audio recording | Working | sounddevice, PipeWire default source |
| STT — faster-whisper | Working | Auto-selected universal fallback |
| STT — mlx-whisper | Working | Apple Silicon, auto-selected |
| STT — Parakeet TDT | Working | NVIDIA ≥ 6 GB VRAM, auto-selected |
| LLM integration | Working | Streaming, tool calling, any OpenAI-compatible endpoint |
| Piper TTS | Working | Sentence-by-sentence streaming while LLM generates |
| Speech preprocessing | Working | `clean_for_speech()` strips markdown/paths before Piper |
| Tools — read/write/shell/clipboard/web | Working | Per-tool trust model, confirmation gate |
| Conversation memory | Working | SQLite, configurable turn window |
| Text input — `rex-ask` / `rex-chat` | Working | Shares memory with voice daemon |
| Project facts — `rex-remember` | Working | Persistent across restarts, injected into every prompt |
| Project context | Working | `.rex/context.md` auto-loaded from working directory |
| Tool call history in context | Working | Recent tool calls injected into LLM prompt |
| Floating pill indicator | Working | GTK4 + gtk4-layer-shell, Wayland only |
| Desktop notification | Working | `notify-send` (Linux), `osascript` (macOS) |
| systemd user service | Working | `~/.config/systemd/user/rex.service` |

## Known issues

- **Bluetooth A2DP clipping** — First syllable of TTS responses may be clipped when the audio
  sink was suspended. `pactl suspend-sink @DEFAULT_SINK@ 0` runs at daemon start to mitigate.
  Does not occur with wired audio.

- **Indicator on non-wlroots compositors** — The floating pill requires a Wayland compositor
  with layer-shell support (Hyprland, Sway, river, etc.). KDE Plasma and GNOME have partial
  support; behaviour may differ. X11 is not supported.

- **`rex-indicator` requires system Python** — `python-gobject` is a system package not
  available via pip. The venv must be created with `--system-site-packages` pointing at the
  system Python. See [HACKING.md](HACKING.md) for setup.

## Next: v0.5 remaining / v0.6

- `rex status` — current state, active project, last query, uptime
- `rex doctor` — checks every dep, config key, file path; pass/fail + fix
- First-run wizard — no manual config editing for the common case

See [docs/roadmap.md](docs/roadmap.md) for the full plan.

# Status

Current version: **v0.0.1** — core pipeline implemented and partially working.

---

## What works

| Component | Status | Notes |
|-----------|--------|-------|
| Hotkey (Super+X) | Working | Hyprland `bindd`/`bindrd` push-to-talk |
| Unix socket IPC | Working | `$XDG_RUNTIME_DIR/rex.sock` |
| Audio recording | Working | Built-in mic via PipeWire default source |
| STT | Working | faster-whisper `tiny.en`, `vad_filter=False`, `no_speech_threshold=1.0` |
| LLM (keyword engine) | Working | Matches: time, date, hello, help |
| Desktop notification | Working | `notify-send` via `_notify()` |
| systemd user service | Working | `~/.config/systemd/user/rex.service` |
| CI | Passing | Lint, type check, tests (88% coverage), typos |

## What is broken

| Component | Status | Issue |
|-----------|--------|-------|
| TTS audio playback | Broken | `aplay` exits 0 from service but produces no sound — see open issue |

## Open issues

- **TTS audio clipping** — First syllable of each response is clipped due to Bluetooth A2DP re-connection delay. `pactl suspend-sink` and silence prefix both tried. Deferred to v0.1 — needs a persistent audio stream or sink keep-alive strategy.

- **Bluetooth HFP mic (SCO link)** — `bluez_input` shows RUNNING in PipeWire but delivers no audio frames when the SCO voice link is not active. Workaround: use built-in mic as default source (`pactl set-default-source alsa_input...`). Bluetooth A2DP works for playback.

- **Whisper hallucinations on silence** — with `no_speech_threshold=1.0`, whisper transcribes silence as dots or garbage. Need a minimum-energy gate before passing audio to STT.

---

## Next: v0.1 — Intelligence

See [docs/roadmap.md](docs/roadmap.md) for full plan.

- Replace keyword engine with Claude API (`claude-haiku`)
- SQLite conversation memory
- Streaming TTS — speak while response is generating
- Config: `[llm]` section with `model` and `api_key`

# Hacking on Rex

This guide is for contributors who want to build, modify, or debug Rex. Read [CONTRIBUTING.md](CONTRIBUTING.md)
first for the contribution workflow. This document covers the technical internals.

---

## Prerequisites

**All platforms**

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) — package and environment manager
- [Piper TTS](https://github.com/rhasspy/piper) — voice synthesis binary (`uv tool install piper-tts`)
- A Piper voice model (`.onnx` file) — see [Installation](docs/installation.md)

**Linux**

```bash
sudo pacman -S portaudio libsndfile   # Arch
sudo apt install portaudio19-dev libsndfile1   # Debian / Ubuntu
```

**macOS**

```bash
brew install portaudio
```

---

## Building from source

```bash
git clone https://github.com/sigil-xyz/rex
cd rex
uv sync --dev
pre-commit install
```

To include an optional STT backend:

```bash
uv sync --dev --extra mlx        # Apple Silicon
uv sync --dev --extra parakeet   # NVIDIA ≥6 GB VRAM
```

---

## Common commands

| Command | Description |
|---------|-------------|
| `just install` | Install dependencies and pre-commit hooks |
| `just dev` | Run daemon in foreground with debug logging |
| `just check` | Run all checks: lint, typecheck, tests, typos |
| `just lint` | Ruff lint and format check |
| `just fix` | Auto-fix all ruff issues |
| `just typecheck` | mypy strict type check |
| `just test` | Run test suite |
| `just cov` | Run tests with HTML coverage report |
| `just typos` | Check for typos |
| `just logs` | Tail live daemon logs via journalctl (Linux) |
| `just service-install` | Install and start systemd user service (Linux) |
| `just service-remove` | Stop and remove systemd user service (Linux) |

---

## Architecture

Rex is a single asyncio process. It listens on a Unix socket and runs a linear pipeline on each
request. No threads. No shared state between requests.

```
rex-trigger (CLI)
      │
      │  unix socket  ($XDG_RUNTIME_DIR/rex.sock  or  /tmp/rex.sock)
      ▼
rex daemon  (asyncio, always running)
      │
      ├── START signal  →  begin audio capture
      │
      └── STOP signal
              │
              ▼
         STT backend  (Parakeet / mlx-whisper / faster-whisper)
         selected at startup based on hardware
              │
              ▼
         LLM response engine  (llm.py)
              │
         ┌────┴────┐
         ▼         ▼
      Piper TTS  notification
    (subprocess)  notify-send (Linux)
    sounddevice   osascript   (macOS)
```

**Design constraints that must be preserved:**

- The daemon is the only long-running process. `rex-trigger` is a thin one-shot client that exits
  after writing to the socket.
- Piper runs as a subprocess, not via Python bindings. This gives clean process isolation — a TTS
  crash cannot bring down the daemon.
- Audio is passed as a `numpy.ndarray` (float32, 16 kHz mono) to the STT backend. faster-whisper
  and mlx-whisper consume it directly. Parakeet writes a temp WAV file, which is deleted after
  transcription.
- The asyncio event loop must never block. CPU-bound work (STT inference, audio playback) runs via
  `loop.run_in_executor`.

---

## Source layout

```
src/rex/
├── __init__.py
├── config.py          — config.toml parsing, dataclasses, defaults
├── daemon/
│   ├── main.py        — asyncio event loop, socket server, pipeline orchestration
│   ├── pipeline.py    — shared LLM+tool pipeline used by daemon and CLI
│   ├── audio.py       — sounddevice recording, start/stop, buffer management
│   ├── stt.py         — backend detection, Transcriber class (Parakeet/mlx/faster-whisper)
│   ├── llm.py         — OpenAI-compatible LLM client, Rex persona
│   ├── tools.py       — tool registry, implementations, trust levels
│   └── tts.py         — Piper subprocess, raw PCM playback via sounddevice
└── cli/
    ├── trigger.py     — unix socket client, sends start/stop, exits immediately
    └── ask.py         — rex-ask (one-shot query) and rex-chat (REPL); no daemon required
```

---

## STT backend selection

`stt._detect_backend()` runs at `Transcriber.load()` time and returns one of:
`"parakeet"`, `"mlx"`, `"faster-whisper"`.

Detection order:

1. macOS + arm64 + `mlx_whisper` importable → `"mlx"`
2. CUDA available + VRAM ≥ 6144 MB + `nemo.collections.asr` importable → `"parakeet"`
3. Otherwise → `"faster-whisper"`

Set `stt.backend` explicitly in config to bypass detection.

---

## Configuration

Rex reads `~/.config/rex/config.toml` at daemon startup. The config is parsed once and held in
memory — a daemon restart is required to pick up changes.

Full reference: [docs/configuration.md](docs/configuration.md). Annotated example:
[config/config.example.toml](config/config.example.toml).

---

## Running tests

```bash
just test
```

- `tests/unit/` — isolated module tests, no external processes required
- `tests/integration/` — full pipeline tests, requires Piper installed

Single file:

```bash
uv run pytest tests/unit/test_stt.py -v
```

With coverage:

```bash
just cov
```

---

## Debugging

**Run in foreground:**

```bash
just dev
```

**Tail service logs (Linux):**

```bash
just logs
```

**Send a trigger manually:**

```bash
rex-trigger start
# speak
rex-trigger stop
```

**Test TTS in isolation:**

```bash
echo "Hello from Rex." | piper-tts \
    --model ~/.local/share/piper/voices/en_US-lessac-medium.onnx \
    --output-raw \
    | python3 -c "
import sys, numpy as np, sounddevice as sd
raw = sys.stdin.buffer.read()
samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32767
sd.play(samples, samplerate=22050); sd.wait()
"
```

**Inspect the socket:**

```bash
ls -la ${XDG_RUNTIME_DIR:-/tmp}/rex.sock
```

---

## Platform notes

### Linux

The daemon installs as a systemd user service tied to the graphical session target. Hotkey binding
is compositor-specific — the recommended setup for Hyprland is in [docs/installation.md](docs/installation.md).

`pactl suspend-sink` runs at startup to prevent PipeWire from suspending the audio sink, which
would cause a Bluetooth A2DP reconnect delay that clips the start of TTS responses. This call is
silently skipped on macOS.

### macOS

Notifications use `osascript` (built-in, no dependencies). The `pactl` sink workaround is skipped
— CoreAudio does not suspend sinks.

For launchd autostart, create a plist at `~/Library/LaunchAgents/xyz.sigil.rex.plist` pointing at
`~/.local/bin/rex`. This is not automated yet — run `rex` manually in the meantime.

---

## Logging

Rex uses Python's standard `logging` module. Level is controlled by `daemon.log_level` in config.

**Linux:**

```bash
journalctl --user -u rex
```

**macOS:**

```bash
log stream --predicate 'process == "rex"'
```

---

## Release process

See the `release` target in `justfile`:

1. Changelog fragments from `changelogs/*.md` are compiled into `CHANGELOG.md`
2. Version is bumped in `pyproject.toml`
3. Commit: `chore: release <version>`
4. Tag: `v<version>`
5. Pushing the tag triggers CI which builds and publishes the release

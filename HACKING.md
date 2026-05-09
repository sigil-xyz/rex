# Hacking on Rex

This guide is for contributors who want to build, modify, or debug Rex. Read [CONTRIBUTING.md](CONTRIBUTING.md) first for the contribution workflow. This document covers the technical internals.

---

## Prerequisites

Before building Rex from source, ensure the following are installed.

**All platforms**

- Python 3.11 or newer
- [uv](https://docs.astral.sh/uv/) — package and environment manager
- [Piper TTS](https://github.com/rhasspy/piper) — voice synthesis binary
- A Piper voice model (`.onnx` file) — see [Installation](docs/installation.md)

**Linux**

```
portaudio libsndfile
```

On Arch Linux:

```
sudo pacman -S portaudio libsndfile
```

**macOS**

```
brew install portaudio
```

---

## Building from Source

Clone the repository and install all dependencies including development extras:

```bash
git clone https://github.com/sigil-xyz/rex
cd rex
uv sync --dev
```

Install pre-commit hooks (required before your first commit):

```bash
pre-commit install
```

---

## Common Commands

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
| `just logs` | Tail live daemon logs via journalctl |
| `just service-install` | Install and start systemd user service |
| `just service-remove` | Stop and remove systemd user service |

---

## Architecture

Rex is a single asyncio process. It listens on a Unix socket and runs a linear pipeline on each request. No threads. No shared state between requests.

```
rex-trigger (CLI)
      │
      │  unix socket  ($XDG_RUNTIME_DIR/rex.sock)
      ▼
rex daemon  (asyncio, always running)
      │
      ├── START signal  →  begin audio capture
      │
      └── STOP signal
              │
              ▼
         STT: faster-whisper
         (model preloaded at daemon startup)
              │
              ▼
         Response engine
         (llm.py — keyword dict in v0.0.1, Claude API in v0.1+)
              │
         ┌────┴────┐
         ▼         ▼
      Piper TTS  notify-send
      (subprocess) (subprocess)
```

**Design constraints that must be preserved:**

- The daemon is the only long-running process. `rex-trigger` is a thin one-shot client that exits after writing to the socket.
- Piper runs as a subprocess, not via Python bindings. This gives clean process isolation — a TTS crash cannot bring down the daemon.
- Audio is passed as a `numpy.ndarray` directly to faster-whisper. No temp files are written to disk.
- The asyncio event loop must never block. Any CPU-bound work (Whisper inference) runs via `loop.run_in_executor`.

---

## Source Layout

```
src/rex/
├── __init__.py
├── config.py          — config.toml parsing, dataclasses, defaults
├── daemon/
│   ├── main.py        — asyncio event loop, socket server, pipeline orchestration
│   ├── audio.py       — sounddevice recording, start/stop, buffer management
│   ├── stt.py         — faster-whisper wrapper, model lifecycle
│   ├── llm.py         — response engine
│   └── tts.py         — piper subprocess, audio playback via aplay/afplay
└── cli/
    └── trigger.py     — unix socket client, sends start/stop/query, exits
```

---

## Configuration

Rex reads `~/.config/rex/config.toml` at daemon startup. The config is parsed once and held in memory — a daemon restart is required to pick up changes.

The full config reference is in [docs/configuration.md](docs/configuration.md). The annotated example is at [config/config.example.toml](config/config.example.toml).

---

## Running Tests

```bash
just test
```

Tests are split into two directories:

- `tests/unit/` — isolated module tests, no external processes required
- `tests/integration/` — full pipeline tests, requires Piper installed

To run a single test file:

```bash
uv run pytest tests/unit/test_stt.py -v
```

To run with coverage:

```bash
just cov
# opens htmlcov/index.html
```

---

## Debugging

**Run the daemon in the foreground:**

```bash
just dev
```

This starts Rex with `log_level = "debug"` and prints all output to the terminal. Ctrl+C to stop.

**Tail service logs:**

```bash
just logs
# equivalent to: journalctl --user -u rex -f
```

**Send a trigger manually (without a hotkey):**

```bash
rex-trigger start
# speak or wait 2 seconds
rex-trigger stop
```

**Test TTS in isolation:**

```bash
echo "Hello from Rex." | piper --model ~/.local/share/piper/en_US-lessac-medium.onnx --output-raw | aplay -r 22050 -f S16_LE -c 1
```

**Inspect the socket:**

```bash
ls -la $XDG_RUNTIME_DIR/rex.sock
```

---

## Platform Notes

### Linux

The daemon installs as a systemd user service and integrates with the graphical session target. Hotkey binding is compositor-specific — the recommended approach for Hyprland is documented in [docs/installation.md](docs/installation.md). Other compositors follow the same pattern using their own keybind mechanism.

Audio I/O uses `sounddevice`, which wraps PortAudio. If the default device is wrong, query available devices:

```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

Set the device name or index in `config.toml` under `[audio] device`.

### macOS

The daemon runs as a launchd user agent (support in v0.1+). Audio I/O and hotkey integration differ from Linux — see `docs/installation.md` for macOS-specific setup.

Piper on macOS is installed via Homebrew. The binary path defaults to `/opt/homebrew/bin/piper`; override via `tts.piper_bin` in config if your setup differs.

---

## Adding a Response (v0.0.1 Response Engine)

The offline response engine in `src/rex/daemon/llm.py` matches keywords in the transcribed text. To add a new response:

1. Add an entry to the `RESPONSES` dict — key is a substring matched case-insensitively, value is a callable returning a string.
2. Add a unit test in `tests/unit/test_llm.py`.
3. Add a changelog fragment in `changelogs/<pr-number>.md`.

The keyword engine is intentionally simple and will be replaced by the Claude API in v0.1. Avoid investing in its complexity.

---

## Logging

Rex uses Python's standard `logging` module. Log level is controlled by `daemon.log_level` in config or the `REX_LOG_LEVEL` environment variable.

On Linux with systemd, logs are routed to the journal and readable via:

```bash
journalctl --user -u rex
```

On macOS, logs go to stderr (captured by launchd) and are readable via Console.app or `log stream --predicate 'process == "rex"'`.

---

## Release Process

See the `release` target in `justfile`. In summary:

1. All `changelogs/*.md` fragments are compiled into `CHANGELOG.md`
2. Version is bumped in `pyproject.toml`
3. A commit is made: `chore: release <version>`
4. The commit is tagged `v<version>`
5. Pushing the tag triggers the release CI workflow, which builds the package and creates a GitHub release

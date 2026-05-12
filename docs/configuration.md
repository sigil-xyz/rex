# Configuration

Rex is configured via `~/.config/rex/config.toml`. The annotated example at
`config/config.example.toml` documents every key. If the file does not exist, Rex starts with
built-in defaults and logs a warning.

## Location

```
~/.config/rex/config.toml
```

## Sections

### `[daemon]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `log_level` | string | `"info"` | `debug`, `info`, `warning`, `error` |
| `recording_timeout` | int | `30` | Max recording duration in seconds before auto-stop |

### `[audio]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `device` | string | `""` | Input device name or index. Empty = system default. |
| `sample_rate` | int | `16000` | Sample rate in Hz. All supported backends expect 16000. |

List available devices:

```bash
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

### `[stt]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `backend` | string | `"auto"` | STT engine — see table below |
| `model` | string | `""` | Model override. Empty = backend default. |
| `device` | string | `"cpu"` | `cpu`, `cuda`, or `auto` — faster-whisper only |

**Backend options:**

| Value | Engine | Hardware required | Default model |
|-------|--------|-------------------|---------------|
| `"auto"` | Detected at startup | — | — |
| `"parakeet"` | NVIDIA Parakeet TDT 0.6B v2 | CUDA, ≥6 GB VRAM | `nvidia/parakeet-tdt-0.6b-v2` |
| `"mlx"` | mlx-whisper large-v3 | Apple Silicon | `mlx-community/whisper-large-v3-mlx` |
| `"faster-whisper"` | Whisper large-v3 int8 | Any | `large-v3` |

`"auto"` selects `parakeet` → `mlx` → `faster-whisper` in order of preference based on available
hardware and installed extras.

### `[tts]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `piper_bin` | string | `"piper-tts"` | Piper binary name or path. Resolved via PATH. |
| `model` | string | — | Path to `.onnx` voice model. **Required.** |

Download voices from [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices).

### `[llm]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api_key` | string | `""` | OpenAI-compatible API key |
| `base_url` | string | `"https://api.aicredits.in/v1"` | API endpoint |
| `model` | string | `"anthropic/claude-haiku-4-5"` | Model identifier |
| `max_tokens` | int | `256` | Max tokens in response |

### `[notification]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `true` | Show desktop notification with response text |
| `timeout` | int | `5000` | Display duration in milliseconds (Linux only) |

Notifications use `notify-send` on Linux and `osascript` on macOS. Both are available with no
additional dependencies.

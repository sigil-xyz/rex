# Configuration

Rex is configured via `~/.config/rex/config.toml`. The example file at `config/config.example.toml` documents every available key.

## Location

```
~/.config/rex/config.toml
```

If the file does not exist, Rex uses built-in defaults and logs a warning.

## Sections

### `[daemon]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `socket_path` | string | `$XDG_RUNTIME_DIR/rex.sock` | Unix socket path |
| `log_level` | string | `"info"` | `debug`, `info`, `warning`, `error` |

### `[audio]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `device` | string | `""` | Input device name or index. Empty = system default. |
| `sample_rate` | int | `16000` | Sample rate in Hz. Whisper requires 16000. |
| `min_duration` | float | `0.5` | Minimum recording seconds. Prevents accidental triggers. |

### `[stt]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `model` | string | `"tiny.en"` | Whisper model. Options: `tiny.en`, `base.en`, `small.en` |
| `device` | string | `"cpu"` | `cpu` or `cuda` |

### `[tts]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `piper_bin` | string | `"/usr/bin/piper"` | Path to piper binary |
| `model` | string | — | Path to `.onnx` voice model. **Required.** |
| `device` | string | `""` | Output device. Empty = system default. |

### `[notification]`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enabled` | bool | `true` | Show desktop notification with response |
| `timeout` | int | `5000` | Notification timeout in milliseconds |

## Environment Variables

| Variable | Overrides |
|----------|-----------|
| `REX_CONFIG_PATH` | Config file path |
| `REX_LOG_LEVEL` | `daemon.log_level` |

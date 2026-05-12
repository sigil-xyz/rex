# Architecture

## System overview

Rex is a Unix daemon with a linear request-response pipeline. The daemon is always running; models
are preloaded at startup; latency is minimized.

```
[User: hold hotkey]
        │
        │  exec rex-trigger start
        ▼
[rex-trigger CLI]  ──unix socket──▶  [rex daemon]
                                           │
                                     start audio capture
                                           │
[User: release hotkey]                     │
        │                                  │
        │  exec rex-trigger stop           │
        ▼                                  ▼
[rex-trigger CLI]  ──unix socket──▶  stop audio capture
                                           │
                                           ▼
                                    [STT backend]
                                     transcribed text
                                           │
                                           ▼
                                    [LLM response engine]
                                     response text
                                           │
                               ┌───────────┴───────────┐
                               ▼                       ▼
                        [Piper TTS]             [notification]
                     sounddevice playback    notify-send / osascript
```

## Component boundaries

| Component | Process | Lifetime |
|-----------|---------|---------|
| `rex` daemon | systemd service (Linux) / foreground (macOS) | always-on |
| `rex-trigger` | one-shot exec | dies after socket write |
| STT model | loaded in daemon at startup | daemon lifetime |
| Piper TTS | subprocess per response | per response |
| sounddevice playback | thread (via executor) | per response |

## STT backends

Rex selects the best available backend at startup when `backend = "auto"`:

| Priority | Backend | Condition |
|----------|---------|-----------|
| 1 | Parakeet TDT 0.6B v2 | Apple Silicon? No. CUDA available + ≥6 GB VRAM + nemo-toolkit installed |
| 2 | mlx-whisper large-v3 | macOS + arm64 + mlx-whisper installed |
| 3 | faster-whisper large-v3 | Always available (fallback) |

The backend is resolved once. It does not change while the daemon is running.

## IPC protocol

Unix socket at `$XDG_RUNTIME_DIR/rex.sock` (Linux) or `/tmp/rex.sock` (macOS).

Messages are newline-terminated strings:

```
start\n
stop\n
```

## Data flow — audio

```
sounddevice → float32 numpy array (16 kHz mono)
    │
    ├── faster-whisper / mlx-whisper: passed directly as numpy array
    │
    └── parakeet: written to temp WAV → NeMo transcribe → temp file deleted
```

## Memory profile (approximate)

| State | RAM |
|-------|-----|
| Daemon idle, no model loaded | ~25 MB |
| + faster-whisper large-v3 int8 | ~1.5 GB VRAM (or RAM on CPU) |
| + Parakeet TDT 0.6B v2 | ~5 GB VRAM |
| + mlx-whisper large-v3 | ~3 GB unified memory |
| During TTS (Piper subprocess) | +50 MB briefly |

## Platform differences

| Concern | Linux | macOS |
|---------|-------|-------|
| Socket path | `$XDG_RUNTIME_DIR/rex.sock` | `/tmp/rex.sock` |
| Notifications | `notify-send` | `osascript` |
| Audio sink keep-alive | `pactl suspend-sink` (PipeWire) | not needed (CoreAudio) |
| Service management | systemd user service | manual / launchd |

## Future: tool interface (v0.2+)

Not yet designed. See `docs/roadmap.md`.

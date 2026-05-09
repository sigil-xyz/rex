# Architecture

## System Overview

Rex is a Unix daemon with a linear request-response pipeline. The daemon is always running; models are preloaded; latency is minimized.

```
[User: hold SUPER+Space]
        │
        │  exec rex-trigger start
        ▼
[rex-trigger CLI]  ──unix socket──▶  [rex daemon]
                                           │
                                     start audio capture
                                           │
[User: release SUPER+Space]                │
        │                                  │
        │  exec rex-trigger stop           │
        ▼                                  ▼
[rex-trigger CLI]  ──unix socket──▶  stop audio capture
                                           │
                                           ▼
                                    [STT: faster-whisper]
                                     transcribed text
                                           │
                                           ▼
                                    [Response engine]
                                     response text
                                           │
                               ┌───────────┴───────────┐
                               ▼                       ▼
                        [Piper TTS]             [notify-send]
                        audio playback          desktop notification
```

## Component Boundaries

| Component | Process | Lifetime |
|-----------|---------|---------|
| `rex` daemon | systemd user service | always-on |
| `rex-trigger` | one-shot exec | dies after socket write |
| Whisper model | loaded in daemon | daemon lifetime |
| Piper TTS | subprocess | per response |
| aplay | subprocess | per response |

## IPC Protocol

Unix socket at `$XDG_RUNTIME_DIR/rex.sock`.

Messages are newline-terminated JSON:

```json
{"action": "start"}
{"action": "stop"}
{"action": "query", "text": "what time is it"}
```

## Memory Profile (target)

| State | RAM |
|-------|-----|
| Daemon idle (no model) | ~25MB |
| Daemon + Whisper tiny.en | ~175MB |
| During TTS (Piper subprocess) | +50MB briefly |

## Data Flow — Audio

```
sounddevice → float32 numpy array → faster-whisper → str
```

No temp files. Audio stays in memory and is discarded after transcription.

## Future: Tool Interface (v0.2+)

Not yet designed. See `docs/roadmap.md`.

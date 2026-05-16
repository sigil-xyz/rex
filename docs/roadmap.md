# Roadmap

Rex is built incrementally. Each version ships a working, stable layer before the next is added.

---

## v0.0.1 — Core Loop (current)

**Goal:** Prove the pipeline works end-to-end.

- [x] Push-to-talk via Hyprland hotkey
- [x] On-device STT with faster-whisper `tiny.en`
- [x] Keyword-based offline response engine
- [~] Voice output via Piper TTS (working, audio quality needs tuning)
- [x] Desktop notification via notify-send
- [x] systemd user service
- [x] Unix socket IPC

No API. No memory. No tools. Just the loop.

---

## v0.1 — Intelligence

**Goal:** Replace the keyword engine with a real LLM.

- [x] Claude API integration (claude-haiku via OpenAI-compatible gateway)
- [x] Persistent conversation memory (SQLite, configurable turn window)
- [x] Config: API key and model management via `~/.config/rex/config.toml`
- [x] Streaming TTS — speak while response is generating

---

## v0.2 — Tool Use

**Goal:** Rex can take actions, not just answer.

- [x] Tool interface design — trust levels (read/write/execute), sandboxed, auditable
- [x] File read/write tool
- [x] Shell command tool (confirmation gate + blocklist)
- [x] Web search tool (ddgr, no API key)
- [x] Clipboard read/write (wl-paste / wl-copy)

---

## v0.3 — Project Scaffolding

**Goal:** Rex creates project structures on request.

- [ ] Template library: Python, Go, Rust, web
- [ ] "Rex, scaffold a FastAPI project called X" → creates directory + files
- [ ] Custom templates via `~/.config/rex/templates/`
- [ ] git init + initial commit

---

## v0.4 — System Monitoring

**Goal:** Rex watches for anomalies and alerts.

- [ ] ClamAV integration — watch Downloads, /tmp, home
- [ ] Process anomaly detection — new SUID binaries, unexpected listeners
- [ ] Network monitoring — new listening ports via `ss`
- [ ] File integrity baseline — sha256 + inotify on critical dirs
- [ ] Proactive alerts via voice + notification

---

## v1.0 — Stable Release

**Goal:** Reliable, packaged, documented for others to use.

- [ ] AUR package
- [ ] Comprehensive docs site (MkDocs)
- [ ] Multi-distro support (Fedora, Ubuntu)
- [ ] Plugin interface for community extensions
- [ ] Performance: <1.5s end-to-end latency

---

## Out of Scope (permanently)

- Wake word / always-on microphone
- Windows or macOS support
- GUI configuration panel
- Cloud sync of memory or goals

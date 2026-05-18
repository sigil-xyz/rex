# Known Issues

Issues that exist in the current codebase and should be resolved in parallel
with ongoing feature work. Ordered by impact.

Each issue notes which milestone it blocks or degrades.

---

## Critical — Breaks Core UX

### ISS-001 · PTT hotkey unreliable on Hyprland

**Symptom:** Recording never stops when the key is released. Every session hits
the 30-second timeout regardless of how long the user spoke.

**Root cause:** Hyprland's `bindr` (release bind) for modifier+key combinations
does not fire when the modifier (`Super`) is released before the main key (`X`).
The `stop` command is never sent to the daemon.

**Impact:** Every voice query takes 30+ seconds. The assistant is unusable in
its current form for push-to-talk.

**Fix:** Replace `bind`/`bindr` pair with a single `bind` toggle in Hyprland
config, and implement a `SpeechSession` state machine in the daemon that
auto-stops on end-of-speech detection. Tracked as v0.6.0 milestone.

**Workaround:** None. Use `rex-ask` (text mode) until v0.6.0 ships.

---

### ISS-002 · Ambient noise transcribed as speech

**Symptom:** When recording is triggered, any sound — music, TV, background
conversation — is passed to the STT engine and transcribed as words. The
resulting garbage text hits the LLM and produces a spoken response.

**Root cause:** The `AudioRecorder` buffers every frame from stream open to
`recorder.stop()`. There is no speech onset detection. Anything captured
during the recording window is treated as intentional input.

**Impact:** Wasted STT inference (~1–2s), wasted LLM inference (~3–5s), and
Rex speaking a response to noise. In noisy environments Rex is unusable.

**Fix:** `SpeechSession` with onset detection (N consecutive frames above RMS
threshold) and a confidence gate post-STT (discard < 3 words). Tracked as v0.6.0.

---

### ISS-003 · STT CUDA backend crashes — `libcublas.so.12` not found

**Symptom:** Setting `device = "cuda"` in `[stt]` config causes the daemon to
crash when the first transcription is attempted.

**Root cause:** `faster-whisper` requires `libcublas.so.12` from the CUDA
toolkit at runtime. The library is not installed on this system.

**Impact:** STT runs on CPU only (`tiny.en` ~2–5s per query). GPU acceleration
for STT is unavailable, adding latency.

**Fix:** Install the CUDA toolkit (`sudo pacman -S cuda`), or accept CPU-only
STT and use `tiny.en` to minimise latency. Note: with llama-server occupying
most of the 4 GB VRAM, running STT on GPU simultaneously may cause OOM.

**Workaround:** Keep `device = "cpu"` and `model = "tiny.en"` in `[stt]`.

---

## High — Degrades Quality

### ISS-004 · Local LLM latency 5–20s per query

**Symptom:** Responses from the local Qwen 3B model take 5–20 seconds
depending on query length and GPU load.

**Root cause:** GTX 1650 (4 GB VRAM) is entry-level for LLM inference.
Qwen 3B Q4_K_M generates ~30–50 tokens/s on this hardware. First-token latency
is ~2–3s due to prompt processing. Longer responses compound this.

**Impact:** Rex feels sluggish for any query that requires more than 1–2 sentences.

**Partial fixes:**
- Keep system prompt strict (2–3 sentences max) — already enforced
- Reduce `max_tokens` for voice mode specifically
- Consider smaller model (1.5B) if quality is acceptable

**Long-term fix:** Upgrade GPU, or implement adaptive model selection
(fast small model for voice, larger model for text queries).

---

### ISS-005 · Recording timeout too conservative (30s)

**Symptom:** When PTT release fails (ISS-001), the daemon waits a full 30
seconds before forcing a stop. This is the primary source of "the assistant
took 30 seconds" complaints.

**Root cause:** `DaemonConfig.recording_timeout` defaults to 30s.
This was chosen to allow long voice queries but is too long for the common case.

**Impact:** Amplifies ISS-001. Every failed release = 30s penalty.

**Fix:** Reduce default to 10s in `config.py`. Tunable via `[daemon].recording_timeout`.
Tracked as part of v0.6.0 (`SpeechSession` replaces the timeout as the primary
stop mechanism).

---

### ISS-006 · `respond_with_tool_result()` is dead code

**File:** `src/rex/daemon/llm.py:165–219`

**Symptom:** The function exists, has a docstring promising "planned for v0.4",
but is never called anywhere in the codebase.

**Impact:** Dead code inflates the module, confuses contributors, and the
docstring promise is never fulfilled.

**Fix:** Either implement it (requires a second LLM call after tool execution,
which was intentionally deferred for latency reasons) or delete it and remove
the planned note. Currently leaning toward deletion — tool results are already
formatted locally in `pipeline.py` and performance is more important than
richer summaries at this stage.

---

## Medium — Correctness or Maintainability

### ISS-007 · Indicator daemon leaks if killed mid-state

**Symptom:** If the Rex daemon crashes or is killed while the indicator is
showing "thinking", the indicator stays visible indefinitely. There is no
watchdog or heartbeat between the daemon and the indicator process.

**Impact:** Stale "thinking" spinner on screen until manually killed or
`rex-indicator quit` is run.

**Fix:** The indicator should timeout any non-idle state after N seconds
(e.g. "thinking" reverts to hidden after 60s without a follow-up signal).
Alternatively, the daemon should send `hide` in its shutdown handler.

---

### ISS-008 · No test coverage for `SpeechSession` (planned)

**Context:** v0.6.0 will introduce `SpeechSession` with a state machine,
energy-based onset detection, and end-of-speech logic. This code runs in
an audio callback thread and is difficult to test without real audio hardware.

**Risk:** Regressions in the state machine (double-start, missed transitions)
will be invisible until runtime.

**Fix:** Unit tests using synthetic numpy audio arrays (sine waves for speech,
silence arrays for quiet frames) that exercise each state transition without
sounddevice. Must be written alongside the implementation, not after.

---

### ISS-009 · Memory usage peaks at 1.2 GB

**Observed:** `systemd` reports `1.2G memory peak` after a session.

**Root cause:** faster-whisper loads the whisper model into memory at startup
and keeps it resident. Each transcription call also allocates temporary buffers.
`gc.collect()` is called after transcription but may not be sufficient.

**Impact:** On machines with 8 GB RAM or less, Rex competes with the llama-server
(~2 GB) and browser for memory.

**Fix:** Profile the allocation with `tracemalloc`. If the model is the dominant
consumer, this is expected behaviour. If temporary buffers are not freed,
investigate faster-whisper's internal cleanup.

---

### ISS-010 · `[stt].device` ignored at startup if set to `cuda` without cuBLAS

**Symptom:** The daemon starts successfully and logs "faster-whisper loaded:
small.en on cuda", but crashes silently on the first transcription with a
`RuntimeError` that is only logged as a task exception — not surfaced to the user.

**Root cause:** `Transcriber.load()` validates the backend at startup but does
not validate CUDA library availability until inference is attempted.

**Impact:** User sees the daemon start, presses the hotkey, speaks — and gets
no response and no audio error. The failure is invisible.

**Fix:** In `stt.py`, attempt a minimal CUDA operation during `load()` and fall
back to CPU with a logged warning if it fails. Never let the device mismatch
surface as a silent crash on the first query.

---

## Tracking

| ID | Title | Severity | Milestone |
|----|-------|----------|-----------|
| ISS-001 | PTT hotkey unreliable | Critical | v0.6.0 |
| ISS-002 | Ambient noise transcribed | Critical | v0.6.0 |
| ISS-003 | STT CUDA crashes (cuBLAS) | Critical | Workaround available |
| ISS-004 | Local LLM latency | High | Hardware-bound |
| ISS-005 | Recording timeout 30s | High | v0.6.0 |
| ISS-006 | Dead code in `llm.py` | High | Next cleanup PR |
| ISS-007 | Indicator state leak | Medium | v0.6.0 |
| ISS-008 | No tests for SpeechSession | Medium | v0.6.0 |
| ISS-009 | Memory peak 1.2 GB | Medium | Needs profiling |
| ISS-010 | CUDA fallback silent fail | Medium | v0.6.0 |

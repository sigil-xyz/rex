# Roadmap

Rex is built incrementally. Each version ships something genuinely useful
on its own — not a stepping stone to tolerate, but a complete, stable layer
the next version builds on.

The full vision is in [IDEA.md](IDEA.md).
The philosophy is simple: **ship working software, be honest about where it is,
never fake progress.**

---

## How Rex Is Built

- **No version ships until it is stable.** Features that work 80% of the time don't ship.
- **Docs ship with code.** If the documentation doesn't reflect reality, the version isn't done.
- **Each version has one sentence that describes what became possible.**
  If you can't write that sentence, the version isn't coherent.
- **The bar is high.** Rex has microphone access, file write, and shell execution.
  Correctness is not optional.

---

## Origin — Where This Started

> _"I genuinely like the idea of AI being my OS — not in the sense of Claude Code
> or an IDE plugin, but greatly inspired by JARVIS from Iron Man. An assistant
> that creates project structures, remembers your goals, helps maintain your
> system, and responds to voice or keymap — locally, privately, always there."_

That is the idea Rex is built toward. The roadmap below is the honest,
specific path from that idea to something real. Each version is one step
further from "daemon that responds" toward "assistant that knows you."

---

## Shipped

### v0.0.1 — Core Loop

> _The pipeline exists. The idea is technically possible._

- [x] Push-to-talk via Hyprland hotkey
- [x] On-device STT — faster-whisper `tiny.en`
- [x] Keyword-based offline response engine _(no LLM)_
- [x] Voice output via Piper TTS
- [x] Desktop notification via `notify-send`
- [x] systemd user service
- [x] Unix socket IPC

**What became possible:** Rex existed. It could be triggered and could respond.

---

### v0.1.0 — Intelligence

> _Rex stops being a keyword matcher and starts reasoning._

- [x] LLM integration — Claude Haiku via OpenAI-compatible gateway
- [x] Persistent conversation memory — SQLite, configurable turn window
- [x] Streaming TTS — Rex speaks while the LLM is still generating
- [x] Config management — `~/.config/rex/config.toml`

**What became possible:** Rex could hold a real conversation and remember
what was said across a session.

---

### v0.2.0 — Tool Use

> _Rex stops answering and starts doing._

- [x] Tool interface — trust levels (`read` / `write` / `execute`), sandboxed, auditable
- [x] `read_file`, `write_file`, `shell`, `web_search`, `clipboard` read/write
- [x] Confirmation state machine — PTT press cancels pending confirmation timeout
- [x] Three STT backends — Parakeet (NVIDIA ≥6 GB), mlx-whisper (Apple Silicon),
      faster-whisper (universal fallback)
- [x] macOS notification support via `osascript`

**What became possible:** Rex could act on your machine — not describe how
to do something, but do it.

---

### v0.2.1 — Correctness

> _What exists works correctly for everyone, not just the author._

- [x] Fix `just dev` passing `--dev` flag that daemon did not accept
- [x] Bump version and license in `pyproject.toml`
- [x] Wire `get_recent_tool_calls()` into LLM context
- [x] `max_tokens` 256 → 1024
- [x] Dead code and stale docs removed

**What became possible:** A stranger installs Rex and gets a working system.

---

### v0.3.0 — Text Input

> _Rex works without voice. The input method stops being a constraint._

- [x] `rex-ask <question>` — one-shot text query, no daemon required
- [x] `rex-chat` — persistent REPL with shared memory
- [x] Output auto-detects from input method (`auto` / `voice` / `text` / `notify-only`)
- [x] Dependency errors surfaced clearly, never silenced
- [x] `pipeline.py` — shared LLM+tool pipeline across voice and text paths

**What became possible:** Rex is usable in every situation.
The assistant doesn't change. Only the interface does.

---

### v0.4.0 — Project Memory

> _Rex remembers what you are working on. Context survives restarts._

- [x] `facts` table in `memory.db` — persistent user facts across restarts
- [x] `rex-remember` CLI — save, list, and forget facts by index
- [x] `MemoryConfig` — `[memory]` config section
- [x] `_load_project_context()` — reads `.rex/context.md` from cwd, injects into every prompt
- [x] Recent tool call history injected into LLM context

**What became possible:** Rex accumulates knowledge about you over time.

---

### v0.5.0 — Presence

> _Rex is visible. You know it heard you, and you know what it's doing._

- [x] `rex-indicator` — GTK4 + gtk4-layer-shell floating pill overlay for Wayland
  - States: listening (red dot), thinking (spinner), done (green), error (amber)
  - Tokyo Night palette, top-centre, input passthrough
  - Auto-starts on first `show` command
- [x] `tts.clean_for_speech()` — strips markdown, humanises paths and units,
      replaces symbols before every Piper call
- [x] Rewritten system prompt — 2–3 sentence cap, contractions, no markdown, dry tone
- [x] `uv.toml` — `python-preference = only-system` for GTK4 site-packages

**What became possible:** Rex communicates its state. The voice loop feels like
a real interaction, not a black box.

---

## In Progress

### v0.6.0 — Reliable Voice Input

> _Rex only processes speech. Noise is ignored. Recordings end when you stop talking._

The push-to-talk model has a fundamental flaw: Hyprland's `bindr` fails when
the modifier key is released before the main key. This means recordings always
hit the 30-second timeout, accumulate ambient noise, and waste STT + LLM cycles
on garbage transcriptions.

This version fixes voice input at the architecture level.

**PTT redesign — toggle + speech session:**

- [ ] `rex-trigger toggle` — press once to arm, press again to disarm (no release binding)
- [ ] `SpeechSession` state machine in `audio.py`:
  - `ARMED` — stream open, listening but not buffering
  - `ONSET` — N consecutive frames above energy threshold confirms real speech
  - `RECORDING` — buffering speech
  - `END_OF_SPEECH` — M frames of silence after speech triggers auto-stop
  - `TIMEOUT` — no speech detected within T seconds → silent discard, no STT
- [ ] Confidence gate in pipeline — discard transcriptions < 3 words or empty
- [ ] `[vad]` config section — thresholds, silence duration, onset timeout, all tunable
- [ ] Hyprland keybind updated to single `bind` (toggle, no `bindr`)
- [ ] Recording timeout reduced to 10s (from 30s)

**What becomes possible:** Rex only responds to you speaking to it.
Ambient noise, accidental triggers, and silence produce no output.

---

## Planned

### v0.3 — Text Input

> _Rex works without voice. The input method stops being a constraint._

- [x] `rex-ask "your question"` — one-shot CLI query, responds in terminal
- [x] `rex-chat` — persistent interactive terminal session
- [x] Output auto-detects from input method
      _(voice in → voice out, text in → text out)_
- [x] `[output].mode` config key: `auto` / `voice` / `text` / `notify-only`
- [x] Dependency errors spoken or printed clearly, never silenced
- [x] Same memory, same tools, same project context regardless of input

**What became possible:** Rex is usable in every situation.
The assistant doesn't change. Only the interface does.

---

### v0.4 — Project Memory

> _Rex remembers what you are working on. Context survives restarts._

- [x] `facts` table — persistent user facts saved across sessions via `rex-remember`
- [x] `rex-remember` CLI — save, list, forget facts by index
- [x] Project context — `.rex/context.md` auto-injected from the working directory
- [x] `tool_calls` history injected into LLM context (name, args, result, status)
- [x] `MemoryConfig` — `[memory]` config section with `recent_tool_calls` and
      `project_context_path`

**What became possible:** Rex accumulates knowledge about you and your project.
Session 100 is meaningfully different from session 1.

---

### v0.5 — Voice Quality & Presence

> _Rex sounds like a colleague, not a document reader. You know when it's listening._

No manual config editing for the common case.
No silent failures. No reading docs before anything works.

- [ ] First-run wizard _(terminal, runs when no `config.toml` exists)_
- [ ] `rex --setup` — re-runnable, each step individually skippable
- [ ] API key validated live — _"Testing connection... ✓"_
- [ ] Explicit tool opt-in with plain-English explanation per tool
- [ ] Missing dependency shown with distro-specific install command
- [x] Floating pill indicator — GTK4 + gtk4-layer-shell, Tokyo Night theme, Wayland
      (`listening` / `thinking` / `done` / `error` states, auto-dismiss, click-through)
- [x] `tts.clean_for_speech()` — strips markdown, rewrites paths and units before Piper
- [x] Rewritten system prompt — 2–3 sentence limit, contractions, no markdown, dry tone
- [ ] `rex status` — current state, active project, last query, uptime
- [ ] `rex doctor` — checks every dep, config key, file path; pass/fail + fix
- [ ] First-run wizard _(no `config.toml` detected)_

**What becomes possible:** Rex feels present and intentional, not robotic.

---

### v0.8.0 — Context Awareness

> _Rex knows what is on your screen without being asked._

- [ ] Active window detection — `hyprctl activewindow`
- [ ] Neovim socket — current buffer, active file, cursor, LSP diagnostics
- [ ] Git context — branch, staged changes, last 3 commits
- [ ] Environment state auto-injected into LLM prompt when relevant
- [ ] _"Explain this"_ → Rex reads current Neovim buffer, responds
- [ ] _"What's broken?"_ → Rex reads diagnostics, responds

**What becomes possible:** Rex understands what you're looking at.
The gap between question and context collapses.

---

### v0.9.0 — Scaffolding

> _Rex creates real projects. The first capability no chatbot can replicate._

- [ ] Template library: Python, Go, Rust, Next.js, FastAPI
- [ ] _"Rex, scaffold a FastAPI project called X"_ →
      full directory + files + `git init` + initial commit
- [ ] Custom templates via `~/.config/rex/templates/`
- [ ] Scaffold automatically sets active project context

**What becomes possible:** _"Rex, scaffold a Rust CLI called orbit."_
One sentence. Immediate visible result.

---

### v0.10.0 — System Monitoring

> _Rex watches your machine and tells you when something needs attention._

- [ ] File integrity baseline — sha256 + inotify on critical dirs
- [ ] Process anomaly detection — new SUID binaries, unexpected listeners
- [ ] Network monitoring — new listening ports via `ss`
- [ ] ClamAV integration — watch Downloads, /tmp, home directory
- [ ] Proactive alerts via voice + desktop notification

**What becomes possible:** Rex is security infrastructure, not just a conversational layer.

---

### v0.11.0 — Plugin System

> _Rex is extensible. The community builds for their field._

- [ ] Plugin interface spec — Python, sandboxed, declared trust level
- [ ] Plugin manifest — name, version, tools exposed, trust requirements
- [ ] Loader from `~/.config/rex/plugins/`
- [ ] Plugins register tools into `REGISTRY` at load time
- [ ] Example plugins: pomodoro, note capture, git workflow
- [ ] Plugin authoring guide for contributors

**What becomes possible:** A developer's Rex looks different from a designer's.

---

### v1.0 — Public Release

> _Anyone can install Rex and be working in 10 minutes._

**Packaging:**

- [ ] AUR package — `rex` in the Arch User Repository
- [ ] Homebrew tap — `brew install sigil-xyz/rex/rex`
- [ ] Nix flake
- [ ] `curl` install script

**macOS first-class:**

- [ ] `launchd` plist generation automated
- [ ] `skhd` / Karabiner setup documented and tested
- [ ] macOS CI runner alongside Linux

**Quality:**

- [ ] `tests/integration/` populated — full pipeline tests with Piper
- [ ] Performance: < 1.5 s end-to-end on mid-range hardware, measured
- [ ] Fedora, Ubuntu, Debian tested in CI

**What becomes possible:** Rex is ready for people who didn't build it.

---

## Publication & Growth

### On v0.9.0 — Show HN

This is the milestone with a one-sentence demo.

> _"Show HN: Rex — local AI assistant that scaffolds projects,
> remembers your work, and runs on your machine. No cloud."_

- Record a 45-second terminal screencast: voice → project created
- Cross-post: r/linux, r/selfhosted, r/neovim
- Goal: 200–500 stars, first external contributors

### On v1.0 — Website + Broader Press

- Launch `rex.sigil.xyz`
- Hacker News, GitHub Trending, tldr.tech, FOSS Weekly
- Goal: 1000+ stars, AUR adoption, first third-party plugins

---

## Out of Scope — Permanently

|                                   | Why                                            |
| --------------------------------- | ---------------------------------------------- |
| Wake word / always-on microphone  | Privacy and CPU cost. Non-negotiable.          |
| Cloud sync of memory or goals     | Everything stays on your machine.              |
| GUI configuration panel           | The wizard is enough. Rex is not an app.       |
| Telemetry of any kind             | There is no server to phone home to.           |
| Multi-user / server mode          | Rex is personal infrastructure, not a service. |
| Forcing voice when text is better | The input method is the user's choice.         |

---

_Rex is free software — [GPL v3.0](LICENSE)_
_© 2026 [sigil-xyz](https://github.com/sigil-xyz)_

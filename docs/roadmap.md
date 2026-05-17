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

The proof of concept. No intelligence. No memory. No tools.
Just the loop: hotkey → voice → transcription → response → speech.

- [x] Push-to-talk via Hyprland hotkey
- [x] On-device STT — faster-whisper `tiny.en`
- [x] Keyword-based offline response engine _(no LLM)_
- [x] Voice output via Piper TTS _(audio quality rough, known issue)_
- [x] Desktop notification via `notify-send`
- [x] systemd user service — starts on login
- [x] Unix socket IPC

No API. No memory. No tools. Just the loop.

**What became possible:** Rex existed. It could be triggered and could respond.

---

### v0.1 — Intelligence

> _Rex stops being a keyword matcher and starts reasoning._

- [x] LLM integration — Claude Haiku via OpenAI-compatible gateway
- [x] Persistent conversation memory — SQLite, configurable turn window
- [x] Streaming TTS — Rex speaks while the LLM is still generating
- [x] Config management — `~/.config/rex/config.toml`, API key, model selection

**What became possible:** Rex could hold a real conversation and remember
what was said across a session.

---

### v0.2 — Tool Use

> _Rex stops answering and starts doing._

- [x] Tool interface — trust levels (`read` / `write` / `execute`), sandboxed, auditable
- [x] `read_file` — reads any file you specify
- [x] `write_file` — writes files, always requires verbal confirmation first
- [x] `shell` — runs shell commands, always requires verbal confirmation first
- [x] `web_search` — ddgr, no API key required
- [x] `clipboard` read/write — `wl-paste` / `wl-copy`
- [x] Three STT backends — Parakeet (NVIDIA ≥ 6 GB), mlx-whisper (Apple Silicon),
      faster-whisper (universal fallback), auto-selected at startup

**What became possible:** Rex could act on your machine — not describe how
to do something, but do it.

---

## In Progress

### v0.2.1 — Correctness

> _What exists works correctly for everyone, not just the author._

Not a feature release. The honest cost of moving fast.
Every item is a bug, a stale doc, or a broken promise.

**Silent bugs:**

- [ ] `systemd/rex.service` — fix `ReadWritePaths` so `write_file` works
      on a fresh install _(currently broken without manual edit)_
- [ ] `just dev` — passes `--dev` to daemon which has no such flag. Silent fail.

**Wrong information:**

- [ ] `pyproject.toml` — version `0.0.1` → `0.2.0`, license `MIT` → `GPL-3.0`
- [ ] `docs/architecture.md` — remove "tool interface not yet designed" _(v0.2 shipped)_
- [ ] `.claude/context.md` — rewrite from scratch _(says "no code written yet")_

**Missing documentation:**

- [ ] `config/config.example.toml` — add `[tools]`, `[llm].memory_turns`,
      `[llm].system_prompt` _(all exist, none in the example)_
- [ ] `docs/configuration.md` — add `[tools]` section
- [ ] `CHANGELOG.md` — compile v0.1 and v0.2 fragments _(currently invisible)_

**Dead code and ignored config:**

- [ ] Delete or document `respond_with_tool_result()` dead code in `llm.py:139`
- [ ] Honor `DaemonConfig.socket_path` in `main.py` / `trigger.py`
      _(config key exists, both files ignore it)_
- [ ] Wire `get_recent_tool_calls()` into LLM context
      _(saved to SQLite, never read back)_
- [ ] `llm.py` — `max_tokens` 256 → 1024 _(too low for tool responses)_

**What becomes possible:** A stranger installs Rex and gets a working system,
not a broken one they have to debug before using.

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

- [x] Floating pill indicator — GTK4 + gtk4-layer-shell, Tokyo Night theme, Wayland
      (`listening` / `thinking` / `done` / `error` states, auto-dismiss, click-through)
- [x] `tts.clean_for_speech()` — strips markdown, rewrites paths and units before Piper
- [x] Rewritten system prompt — 2–3 sentence limit, contractions, no markdown, dry tone
- [ ] `rex status` — current state, active project, last query, uptime
- [ ] `rex doctor` — checks every dep, config key, file path; pass/fail + fix
- [ ] First-run wizard _(no `config.toml` detected)_

**What becomes possible:** Rex feels present and intentional, not robotic.

---

### v0.6 — Scaffolding

> _Rex creates real projects. The first capability no chatbot can replicate._

Combined with project memory from v0.4, Rex scaffolds and immediately
knows what you just created. The demo is one sentence.

- [ ] Template library: Python, Go, Rust, Next.js, FastAPI
- [ ] _"Rex, scaffold a FastAPI project called X"_ →
      full directory + files + `git init` + initial commit
- [ ] Custom templates via `~/.config/rex/templates/`
- [ ] Scaffold automatically sets active project context
- [ ] Template variables — name, author, license injected at creation

**What becomes possible:** _"Rex, scaffold a Rust CLI called orbit."_
One sentence. Immediate visible result. No other local assistant does this.

---

### v0.7 — Context Awareness

> _Rex knows what is on your screen without being asked._

The step from "smart assistant" to "ambient assistant."
You stop describing your environment. Rex already knows it.

- [ ] Active window detection — `hyprctl activewindow` / `xdotool`
- [ ] Neovim socket — current buffer, active file, cursor, LSP diagnostics
- [ ] Git context — branch, staged changes, last 3 commits
- [ ] Environment state auto-injected into LLM prompt when relevant
- [ ] _"Explain this"_ → Rex reads current Neovim buffer, responds
- [ ] _"What's broken?"_ → Rex reads diagnostics, responds
- [ ] VS Code extension — same IPC protocol, different editor surface

**What becomes possible:** Rex understands what you're looking at.
The gap between question and context collapses.

---

### v0.8 — System Monitoring

> _Rex watches your machine and tells you when something needs attention._

Proactive, not reactive. Rex speaks without being asked when something
is wrong — not just answers when you ask.

- [ ] File integrity baseline — sha256 + inotify on critical dirs
- [ ] Process anomaly detection — new SUID binaries, unexpected listeners
- [ ] Network monitoring — new listening ports via `ss`
- [ ] ClamAV integration — watch Downloads, /tmp, home directory
- [ ] Proactive alerts via voice + desktop notification
- [ ] Alert threshold config — what Rex watches and how loudly it speaks

**What becomes possible:** Rex is security infrastructure, not just a conversational layer.
It runs in the background and earns its keep even when you're not talking to it.

---

### v0.9 — Plugin System

> _Rex is extensible. The community builds for their field._

Rex core handles understanding, memory, and action.
Plugins define what actions are available.
This is what enables "any field" without core becoming bloated.

- [ ] Plugin interface spec — Python, sandboxed, declared trust level
- [ ] Plugin manifest — name, version, tools exposed, trust requirements
- [ ] Loader from `~/.config/rex/plugins/`
- [ ] Plugins register tools into `REGISTRY` at load time
- [ ] Plugins cannot exceed daemon trust ceiling
- [ ] Example plugins: pomodoro, note capture, git workflow
- [ ] Plugin authoring guide for contributors

**What becomes possible:** A developer's Rex looks different from a designer's.
Rex stops being a developer tool and starts being a platform.

---

### v1.0 — Public Release

> _Anyone can install Rex and be working in 10 minutes._

Rex is, by this point, genuinely better than any alternative for its
specific audience — and ready to grow that audience.

**Packaging:**

- [ ] AUR package — `rex` in the Arch User Repository
- [ ] Homebrew tap — `brew install sigil-xyz/rex/rex`
- [ ] Nix flake
- [ ] `curl` install script — no `git clone` required

**macOS first-class:**

- [ ] `launchd` plist generation automated in `setup.sh`
- [ ] `skhd` / Karabiner setup documented and tested
- [ ] macOS CI runner alongside Linux

**Documentation:**

- [ ] MkDocs documentation site — install, configure, extend, contribute
- [ ] Troubleshooting guide — every known failure with exact fix
- [ ] [IDEA.md](IDEA.md) linked from `CONTRIBUTING.md` and `HACKING.md`
- [ ] `.claude/context.md` added to release checklist

**Quality:**

- [ ] `tests/integration/` populated — full pipeline tests with Piper
- [ ] Performance: < 1.5 s end-to-end on mid-range hardware, measured
- [ ] Fedora, Ubuntu, Debian tested in CI
- [ ] All v0.2.1 debt confirmed resolved

**What becomes possible:** Rex is ready for people who didn't build it.

---

## Publication & Growth

These are not features — they are the moments Rex reaches new people.
Each is tied to a specific version so there is always something real to show.

### On v0.3 — First External Post

Rex can now be used without voice. That is worth saying publicly.

- Post to r/linux, r/selfhosted, r/commandline
- Short post: what changed, why it matters, install link
- Goal: first 50 stars, first 5 issues from people who didn't build Rex

### On v0.6 — Show HN

This is the milestone with a one-sentence demo. The timing is right.

> _"Show HN: Rex — local AI assistant that scaffolds projects,
> remembers your work, and runs on your machine. No cloud."_

- Record a 45-second terminal screencast: voice → project created
- Post Tuesday or Wednesday morning (peak HN traffic)
- Cross-post: r/linux, r/selfhosted, r/neovim (if v0.7 is close)
- Same day: Hashnode post
  _"I'm building a local JARVIS — why I started with a daemon, not an app"_
- Goal: 200–500 stars, first external contributors

### On v0.7 — Neovim Community

Neovim + voice + local context = nothing else exists.

- Post to r/neovim with a Neovim-specific demo
  _"Rex reads your buffer, understands your diagnostics, responds locally"_
- Goal: Neovim users who live in the terminal start contributing

### On v1.0 — Website + Broader Press

Rex is ready for people who didn't build it. Reach them accordingly.

- Launch `rex.sigil.xyz`:
    - Above fold: demo GIF, one-line install, three-word pitch
    - Below fold: philosophy, comparison table, roadmap
- Hashnode: _"Rex 1.0 — a year of building a local JARVIS,
  what we learned"_
- Submit to: Hacker News, GitHub Trending, tldr.tech, FOSS Weekly
- Goal: 1000+ stars, AUR community adoption, first third-party plugins

---

## Website Plan (v1.0)

`rex.sigil.xyz` — static, fast, no JavaScript framework required.

```
/           Landing — demo, install, philosophy
/docs       MkDocs — full documentation
/roadmap    This file, rendered
/plugins    Community plugin registry (post v1.0)
```

**Above the fold must show:**

- Terminal screencast or GIF — Rex doing something, not just text
- One-line install, copy-button
- Three words: _Local. Private. Yours._

**The comparison table** — what gets shared:

|                     | Siri / Google | OpenHuman | Rex |
| ------------------- | ------------- | --------- | --- |
| Fully offline STT   | ✗             | ✗         | ✓   |
| No wake word        | ✗             | ✗         | ✓   |
| Runs shell commands | ✗             | ✓         | ✓   |
| Linux native        | ✗             | ⚠         | ✓   |
| No cloud required   | ✗             | ✗         | ✓   |
| < 30 MB idle        | ✗             | ✗         | ✓   |
| Open source         | ✗             | ✓         | ✓   |
| Text + voice input  | ✓             | ✓         | ✓   |

---

## The Larger Vision (Post v1.0)

Directions, not commitments. Each follows from the architecture already built.
None require Rex to become a different product.

**Local model routing** — Ollama fallback when no API key is set.
The STT and TTS are already local. The LLM is the last cloud dependency.

**Proactive memory** — Rex watches what you do (with explicit consent)
and surfaces relevant context without being asked.

**Mobile companion** — lightweight app sending input to the local Rex daemon
over LAN. Same memory, same tools, mobile input surface.

**Windows support** — the architecture supports it. The tooling and
testing infrastructure don't yet. After v1.0.

**Web UI** — Rex from a browser on the local network for situations
where a terminal isn't appropriate.

**Any user, any field** — the plugin system is the unlock. When anyone
can write a plugin for their domain, Rex grows beyond developers.

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

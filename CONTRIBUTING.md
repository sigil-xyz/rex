# Contributing to Rex

Thank you for your interest. Before you start, read this document fully.

---

## Before You Open Anything

- **Search first.** Issues, discussions, PRs — check all three before creating something new.
- **Features go in Discussions, not Issues.** If you want to propose something new, open a Discussion under "Ideas". Issues are for confirmed, actionable bugs only.
- **Bug fixes** can go straight to a PR. No discussion needed.
- **Non-trivial changes** (architecture, new subsystems, breaking changes) require a Discussion with maintainer sign-off before any code is written.

---

## Setup

```bash
git clone https://github.com/sigil-xyz/rex
cd rex
uv sync --dev
pre-commit install
```

Verify everything works:

```bash
just check
```

---

## Branch Naming

All branches off `main`. Format: `<type>/<short-description>` in kebab-case.

```
feat/voice-wakeword
fix/audio-device-selection
docs/update-architecture
chore/bump-faster-whisper
ci/add-integration-tests
refactor/stt-pipeline
perf/reduce-daemon-memory
```

Rules:
- No uppercase
- No slashes inside the description
- Keep it short — under 40 characters total

---

## Commit Format

Rex follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `ci`, `chore`, `build`

**Scopes:** `daemon`, `stt`, `tts`, `llm`, `audio`, `cli`, `config`, `systemd`, `ci`, `docs`

**Examples:**

```
feat(stt): preload whisper model at daemon startup

fix(audio): handle missing sounddevice with clear error

docs(config): document all config.toml fields

chore: bump faster-whisper to 1.1.0

feat!: rename config key voice_model to tts_model

BREAKING CHANGE: update your config.toml before upgrading
```

Rules:
- Description in lowercase, no trailing period
- Body explains WHY, not WHAT (the diff shows what)
- Breaking changes use `!` and/or `BREAKING CHANGE:` footer

---

## PR Process

1. Branch off `main`
2. Write or update tests for your change
3. Add a changelog fragment to `changelogs/<your-pr-number>.md` (see `changelogs/README.md`)
4. Open a PR using the template
5. CI must be fully green — no exceptions
6. Address all review comments before requesting re-review

**PR size:** Keep PRs small and focused. One concern per PR. If you find yourself writing "and also..." in the summary, split it.

---

## Code Standards

Pre-commit handles formatting and linting automatically on every commit. To run manually:

```bash
just lint       # ruff check + format check
just typecheck  # mypy strict
just test       # pytest
just typos      # spell check
```

Or all at once:

```bash
just check
```

Standards:
- All public functions must have type annotations
- No `Any` without a comment explaining why
- Tests required for all non-trivial logic
- No commented-out code in PRs

---

## Changelog Fragments

Every PR that changes user-visible behavior must include a fragment:

```bash
# changelogs/42.md
Added support for push-to-talk via Hyprland `bindrelease`.
```

See `changelogs/README.md` for format details.

---

## Questions

Use GitHub Discussions → Q&A category. Do not open an issue for questions.

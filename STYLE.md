# Style Guide

Code and documentation conventions for Rex.

---

## Python

- Line length: **100 characters**
- Quotes: **double quotes**
- Type annotations: **required on all public functions**
- No `Any` without an inline comment explaining why
- Imports: stdlib → third-party → internal, separated by blank lines (ruff handles this)

**Naming:**

| Thing | Convention | Example |
|-------|-----------|---------|
| Variables | `snake_case` | `audio_buffer` |
| Functions | `snake_case` | `start_recording()` |
| Classes | `PascalCase` | `DaemonConfig` |
| Constants | `UPPER_SNAKE` | `SOCKET_PATH` |
| Private | leading `_` | `_load_model()` |
| Type aliases | `PascalCase` | `AudioBuffer = np.ndarray` |

**Comments:**

Write comments only when the WHY is non-obvious. Never explain what the code does — the code does that. Never reference the PR, issue number, or task in a comment (that belongs in the commit message).

```python
# Good: explains a non-obvious constraint
# sounddevice requires float32, not the default int16
audio = audio.astype(np.float32)

# Bad: explains what the code already says
# Convert audio to float32
audio = audio.astype(np.float32)
```

**Docstrings:**

One-line max. Only on public module-level functions. No multi-paragraph blocks.

```python
def transcribe(audio: np.ndarray) -> str:
    """Transcribe audio buffer to text using Whisper."""
```

---

## Commits

Follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/). Full format in [CONTRIBUTING.md](CONTRIBUTING.md).

Description rules:
- Lowercase, present tense, imperative: `add`, `fix`, `remove` — not `added`, `fixes`, `removed`
- No trailing period
- Under 72 characters

Body rules:
- Explain WHY, not WHAT
- Wrap at 72 characters
- Blank line between description and body

---

## Documentation (Markdown)

- Wrap at **100 characters**
- Use ATX headings (`#`, not underline style)
- One blank line before and after headings, code blocks, and lists
- Code blocks always have a language tag
- No trailing whitespace
- Single blank line at end of file

---

## TOML (config files)

- 4-space indent
- Group related keys together
- Comment every non-obvious key

---

## Naming: "Rex"

- Written as **Rex** (capitalized, no backticks) when referring to the assistant
- Written as `rex` (lowercase, backtick) when referring to the CLI binary or package
- Never ALL CAPS unless in an environment variable: `REX_CONFIG_PATH`

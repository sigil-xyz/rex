# AI Usage Policy

Rex has a clear policy on AI-assisted contributions. Read this before submitting anything AI-generated.

---

## The Rule

**You must fully understand every line of code you submit, regardless of how it was written.**

AI tools (ChatGPT, Claude, Copilot, etc.) are permitted as writing aids. They are not permitted as a substitute for understanding. If you cannot explain what your code does, why it does it, and what its failure modes are — do not submit it.

---

## What This Means in Practice

**Allowed:**
- Using AI to draft code that you then read, understand, and verify
- Using AI to explain an unfamiliar API or pattern
- Using AI to generate test cases that you review
- Using AI to improve documentation wording

**Not allowed:**
- Copy-pasting AI output without reading it
- Submitting AI-generated code you cannot explain in a review
- Using AI to work around a gap in your understanding of the codebase

---

## Why

AI tools generate plausible-looking code that can be subtly wrong, insecure, or incompatible with the project's design. Rex runs as a background daemon with audio access — the bar for correctness is high. A maintainer who reviews your PR is trusting that you vetted what you submitted. "The AI wrote it" is not an acceptable explanation for a bug.

---

## Disclosure

If a significant portion of your PR was AI-generated, mention it in the PR description. This is not a disqualifier — it is a transparency requirement.

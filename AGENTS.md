# Instructions for AI Agents

This file defines what AI agents (Claude, Copilot, etc.) are allowed to do when contributing to Rex.

---

## Permitted

- Fix bugs with a clear reproduction case
- Improve test coverage for existing behavior
- Update documentation to match current code
- Fix typos and formatting issues
- Bump dependency versions with passing CI

## Requires Human Decision First

- New features — open a Discussion, get sign-off
- Architecture changes — discuss in HACKING.md terms
- New dependencies — justify need and audit package
- Breaking changes — requires explicit maintainer approval
- Changes to CI/CD pipelines

## Prohibited

- Committing directly to `main`
- Skipping CI checks
- Adding code you cannot explain line by line
- Using AI-generated code without understanding it fully

---

## Standards for AI-Generated PRs

If you are an AI agent opening a PR:

1. Run `just check` — all checks must pass
2. Add a `changelogs/<pr-number>.md` fragment
3. State in the PR description that AI generated the code
4. The human reviewer is responsible for understanding and approving every line

---

## Context Files

For project architecture, read:
- `HACKING.md` — internals and design decisions
- `docs/architecture.md` — system diagram and data flow
- `docs/roadmap.md` — what's planned vs. out of scope

For code standards, read:
- `STYLE.md` — naming, formatting, comment rules
- `CONTRIBUTING.md` — branch, commit, PR process

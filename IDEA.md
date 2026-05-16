# The Idea Behind Rex

## The Inspiration

JARVIS.

Not the acronym. Not the Marvel trademark. The _idea_ — an assistant that lives
alongside you, knows what you're working on, takes real action, and gets out of
the way when you don't need it.

In the films, JARVIS wasn't impressive because it could answer questions.
Search engines answer questions. JARVIS was impressive because it understood
Tony's situation without being told. It remembered yesterday's problem. It ran
the diagnostics instead of describing how to run them. It warned him before he
asked. It was, in the most honest sense, infrastructure that thought.

That's the idea Rex is built toward.

---

## The Problem

Every AI assistant available today makes one of three compromises:

**Cloud-first.** Your conversations, your files, your context — all processed
on someone else's server. You don't own what the assistant knows about you.

**Chat-first.** A box you type into, get text back from, then have to act on
yourself. It answers. It doesn't do.

**Interface-first.** An app you open, a window you switch to, a thing you
manage. Ambient it is not.

None of them remember what you were working on last Tuesday unless you tell
them again. None of them notice that your build is failing. None of them live
on your machine, know your filesystem, and stay there permanently.

Rex is built on a different assumption: **your assistant should be infrastructure,
not an application.**

---

## The Philosophy

**It doesn't matter how you talk to it.**

Speak to it at your desk. Type to it in the terminal when you're in a café.
Script it from a shell. The input method is irrelevant. The intelligence
is consistent. The memory is the same. The tools are the same.

**It lives on your machine. Not someone else's.**

Every piece of context Rex holds about you — your projects, your goals,
your conversation history, your tool usage — lives in SQLite on your
local filesystem. Encrypted. Yours. No company sees it. No server touches
it. Rex works offline because privacy isn't a feature, it's a constraint.

**It acts, not just answers.**

The gap between "here's how to rename all these files" and actually renaming
them is the gap between a search engine and an assistant. Rex has tools —
file read/write, shell execution, web search, clipboard — and uses them
when you ask. With your confirmation for anything destructive. But it acts.

**It knows you over time.**

Context that evaporates on restart isn't memory. Rex is being built toward
persistent project awareness — knowing what you're building, what you were
stuck on, what changed since yesterday — so that every conversation starts
from where you actually are, not from zero.

**It should work for anyone.**

Not just developers. Not just Linux users. Not just people who know what
a daemon is. The long-term vision is an assistant anyone can install —
any OS, any hardware, any field — that is genuinely useful from day one.
Rex starts with Linux and macOS, with developers, because that's the honest
first step. It grows from there.

---

## What JARVIS Actually Did (That Matters)

Four capabilities define the JARVIS idea. Everything Rex builds toward maps
to one of these:

**1. Ambient awareness — knowing without being told.**
JARVIS knew the state of the workshop. What was running. What had changed.
What was failing. Rex builds toward this through active window detection,
git state, editor buffer awareness, system monitoring. The assistant sees
your environment so you don't have to describe it.

**2. Persistent memory — context that survives time.**
JARVIS knew Tony's history. Not just the last conversation — the project,
the goal, the obstacle from last week. Rex builds toward this through
structured project memory, goal tracking, and long-term memory summarization
that compresses history without losing what matters.

**3. Real action — doing, not describing.**
JARVIS ran the suit diagnostics. Rerouted the power. Scrambled the signal.
Rex builds toward this through a tool system that executes — files, shell,
web, clipboard — with a trust model that makes destructive actions explicit
and auditable.

**4. Situation awareness — understanding context, not just words.**
"Handle it" meant something different in a crisis than in a workshop.
JARVIS knew the difference. Rex builds toward this by injecting environment
state — active project, recent tool calls, system context — into every
prompt so the LLM reasons about your actual situation.

---

## What Rex Is Not Trying To Be

**Not a product that needs a server.**
Rex has no backend. It has no SaaS layer. There is no Rex account. The
goal is never to monetize your data or require connectivity.

**Not a voice assistant.**
Voice is one input mode. Rex responds to text. Rex can be scripted.
The input method is a detail. The assistant is the point.

**Not a general-purpose chatbot.**
Rex is not trying to compete with Claude or ChatGPT for general knowledge
questions. It's trying to be the thing that knows _your_ machine, _your_
projects, and _your_ context — and can act on that knowledge.

**Not a GUI application.**
Rex is infrastructure. It runs in the background. It doesn't have a window.
The surface layer — how you interact with it — is deliberately minimal
and configurable. Power users get the terminal. Future users get whatever
interface makes sense for them.

**Not finished.**
Rex today is an honest early version of this idea. The core loop works.
The tools work. The memory works. The vision is significantly larger than
what exists right now. That gap is the roadmap.

---

## The Larger Vision

The honest answer to "where does Rex go?" is: everywhere your attention goes.

That means:

- Any input method — voice, text, hotkey, script, eventually mobile
- Any operating system — Linux today, macOS now, Windows eventually
- Any field — a developer's Rex plugin looks different from a designer's,
  which looks different from a doctor's. The core is the same. The tools differ.
- Any hardware — a high-end workstation and a four-year-old laptop should
  both have access to a useful assistant. Local models exist for offline use.
  The cloud API is optional, not required.

The architecture decisions made today — daemon process, input-agnostic IPC,
local SQLite memory, tool registry, plugin system — are chosen because they
scale to that vision. Rex doesn't need to become a different product to get
there. It needs to grow the surface area while keeping the core stable.

---

## The Honest Starting Point

Rex is being built by one developer, in public, incrementally.

The current version is not JARVIS. It's a daemon that listens for a hotkey,
transcribes your voice locally, calls an LLM, uses a handful of tools,
and responds with voice and a notification. That's it.

But the architecture is right. The philosophy is right. The direction is right.

Every version ships something genuinely useful on its own. The scaffolding
version is useful without the context awareness version. The text input version
is useful without the mobile version. Baby steps, each one complete.

The gap between Rex today and the full vision is not a problem to hide.
It's the roadmap.

---

_Rex is free software. Everything it knows about you stays on your machine._
_The vision is ambitious. The code is honest about where it is._
_That's the only way to build something that lasts._

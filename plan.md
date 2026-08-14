# JARVIS — Shared Agent Plan & Change Log

> **MANDATORY READ**: Every agent working on this codebase MUST read this file in full before making any changes.
> After completing work, every agent MUST append a log entry at the bottom of this file describing what was changed and why.

---

## What This File Is

This is the single source of truth for all agents collaborating on the JARVIS project. It serves three purposes:
1. **Context** — summarises the project, its current state, and active priorities so any agent can get up to speed instantly.
2. **Coordination** — prevents agents from duplicating work or undoing each other's changes.
3. **Audit trail** — a chronological log of every meaningful change made to the codebase and the reasoning behind it.

---

## Project Overview

**JARVIS** is a fully local, modular voice AI assistant (no cloud, no API keys) that runs on:
- **GTX 1660 (4 GB VRAM)** — used exclusively by Ollama (LLM + vision model).
- **AMD Ryzen 7 2700X + 32 GB RAM** — used by STT, TTS, VAD, and wake-word detection.

### Core Files at a Glance

| File | Role |
|------|------|
| `jarvis_project/main.py` | Master orchestrator / event loop |
| `jarvis_project/llm.py` | Ollama interface, 18 tool definitions, tool-call loop |
| `jarvis_project/tools.py` | All real-world OS actions (open apps, search, disk, self-modify) |
| `jarvis_project/stt.py` | Microphone capture + faster-whisper transcription (CPU, int8) |
| `jarvis_project/tts.py` | Piper TTS with barge-in support; pyttsx3 fallback |
| `jarvis_project/vad.py` | SpeechInterruptMonitor + UtteranceRecorder |
| `jarvis_project/wakeword.py` | openWakeWord ONNX — detects "Hey Jarvis" |
| `jarvis_project/memory.py` | SQLite-backed conversation + facts memory |

### Non-Negotiable Hardware Rules (Never Break These)
- `faster-whisper` must always use `device="cpu"` and `compute_type="int8"`.
- Piper and pyttsx3 must always run on CPU.
- Ollama (`qwen2.5:3b` + `moondream`) gets the GPU — never load other models on CUDA.
- Do **not** create new virtual environments. Use the existing `.venv`.

### Key Architectural Invariants
- `main.py` imports everything and wires modules together — it must remain the single entry point.
- `vad.py` is only imported by `stt.py` and `tts.py` — do not import it from anywhere else.
- `apply_code_change()` in `tools.py` always creates a backup and runs `py_compile` before writing — never bypass this.
- History is kept in sync between the in-memory `history` list and SQLite after every turn.
- The LLM tool loop caps at 5 rounds to prevent infinite loops.

---

## Current Status

| Area | Status | Notes |
|------|--------|-------|
| Wake Word | ✅ Working | `hey_jarvis.onnx` via openWakeWord |
| STT | ✅ Working | faster-whisper base.en, CPU int8 |
| TTS | ✅ Working | Piper (alan-medium) with barge-in |
| LLM + Tools | ✅ Working | qwen2.5:3b, 18 tools |
| Memory | ✅ Working | SQLite, facts + conversation history |
| Self-Modify | ✅ Working | read/apply/restore with backup |
| Screen Vision | ✅ Working | Moondream via Ollama |
| Web Search | ✅ Working | Playwright (Chromium) |

---

## Active Priorities / Known Issues

> Update this section when you start or finish working on a priority item.

- [ ] No active known bugs at time of file creation.
- [ ] (Add new priorities / bugs here as they are discovered.)

---

## Agent Rules

Before touching any file, an agent must:
1. Read the **full** entry for that file in `CODEBASE_EXPLAINED.md`.
2. Check this file for any in-progress work that could conflict.
3. Run the project and reproduce the issue / verify the feature before writing code.

After finishing work, an agent must:
1. Mark any completed priority items above with `[x]`.
2. Add a new entry to the **Change Log** below.

---

## Change Log

Entries are in reverse-chronological order (newest first).
Each entry MUST follow this template:

```
### [YYYY-MM-DD] — [Agent Name / Model]
**Files changed:** `file1.py`, `file2.py`
**What:** Short description of what was done.
**Why:** Reason — what problem it solved or feature it added.
**Notes:** Anything the next agent needs to know (gotchas, follow-up work, etc.)
```

---

### [2026-08-14] — Antigravity (Gemini)
**Files changed:** `plan.md` *(this file — created)*
**What:** Created `plan.md` as the mandatory shared context and change-log document for all agents working on the Jarvis codebase.
**Why:** Establishes a coordination layer so that multiple agents can work on the codebase without stepping on each other, and so any new agent can instantly understand the project state and history without having to reverse-engineer the code from scratch.
**Notes:** The current codebase is in a stable, working state. All modules are present. No bugs were known at the time of creation. Future agents should update the **Active Priorities** section before starting work and log their changes here when done.

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
| `jarvis_project/llm.py` | Ollama interface, 16 tool definitions, tool-call loop |
| `jarvis_project/tools.py` | All real-world OS actions (open apps, search, disk, self-modify) |
| `jarvis_project/stt.py` | Microphone capture + faster-whisper transcription (CPU, int8) |
| `jarvis_project/tts.py` | Piper TTS with barge-in support; pyttsx3 fallback |
| `jarvis_project/vad.py` | SpeechInterruptMonitor + UtteranceRecorder |
| `jarvis_project/wakeword.py` | openWakeWord ONNX — detects "Hey Jarvis" |
| `jarvis_project/memory.py` | SQLite-backed conversation + facts memory |

### Non-Negotiable Hardware Rules (Never Break These)
- `faster-whisper` must always use `device="cpu"` and `compute_type="int8"`.
- Piper and pyttsx3 must always run on CPU.
- Ollama (`qwen2.5:3b` + `gemma4:e4b`) gets the GPU — never load other models on CUDA.
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
| LLM + Tools | ✅ Working | qwen2.5:3b (Flash), 16 tools, GPU-pinned |
| Memory | ✅ Working | SQLite, facts + conversation history |
| Self-Modify | ✅ Working | read/apply/restore with backup |
| Screen Vision | ⚠️ Model not pulled | `gemma4:e4b` code path wired with `keep_alive=0` |
| Pro Tier | ⚠️ Model not pulled | `qwen3-coder:30b` CPU + `keep_alive=0` code path wired |
| Web Search | ✅ Working | Playwright (Chromium) |

---

## Active Priorities / Known Issues

> Update this section when you start or finish working on a priority item.

- [ ] Pull the remaining tier models: `ollama pull qwen3-coder:30b` (~19 GB) and `ollama pull gemma4:e4b`. Code paths are already wired; they will fail at runtime until pulled.
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

### [2026-08-15] — big-pickle (opencode)
**Files changed:** `jarvis_project/llm.py`, `jarvis_project/tools.py`, `jarvis_project/main.py`, `AGENTS.md`, `plan.md` *(this file)*
**What:** Brought the codebase in line with the final 3-tier architecture spec. `llm.py`: pinned the Flash Tier (`qwen2.5:3b`) fully to the GPU (`num_gpu=-1`) with permanent residency (`keep_alive=-1`), fixed the stale "phi4-mini" docstring. `tools.py`: Pro Tier (`qwen3-coder:30b`) now runs CPU-only (`num_gpu=0`) and unloads after use (`keep_alive=0`); Vision Tier (`gemma4:e4b`) unloads after every screen analysis (`keep_alive=0`). `main.py`: `--text` mode no longer prompts for an audio input mode. Rewrote `AGENTS.md` to document the 3-tier router, the scrapped sandbox loop, and the current 8-file layout.
**Why:** The spec's core hardware-split rules (flash resident in VRAM, pro/vision sleep between calls) were not enforced by the code — models stayed hot in RAM/VRAM and the flash model could be evicted. Enforcing the sleep/wake contract keeps VRAM locked for the real-time voice loop.
**Notes:** `qwen3-coder:30b` and `gemma4:e4b` are NOT installed on this machine yet — pull them before first use (see Active Priorities). The sandbox/self-evolve files were already deleted in commit `bd433e4`; do not reintroduce.

---

### [2026-08-14] — Antigravity (Gemini)
**Files changed:** `plan.md` *(this file — created)*
**What:** Created `plan.md` as the mandatory shared context and change-log document for all agents working on the Jarvis codebase.
**Why:** Establishes a coordination layer so that multiple agents can work on the codebase without stepping on each other, and so any new agent can instantly understand the project state and history without having to reverse-engineer the code from scratch.
**Notes:** The current codebase is in a stable, working state. All modules are present. No bugs were known at the time of creation. Future agents should update the **Active Priorities** section before starting work and log their changes here when done.

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
| `jarvis_project/llm.py` | Ollama interface, 24+ tool definitions, tool-call loop |
| `jarvis_project/tools.py` | All real-world OS actions (open apps, search, disk, self-modify) |
| `jarvis_project/stt.py` | Microphone capture + faster-whisper transcription (CPU, int8) |
| `jarvis_project/tts.py` | Piper TTS with barge-in support; pyttsx3 fallback |
| `jarvis_project/vad.py` | SpeechInterruptMonitor + UtteranceRecorder |
| `jarvis_project/wakeword.py` | openWakeWord ONNX — detects "Hey Jarvis" |
| `jarvis_project/memory.py` | SQLite-backed conversation + facts memory |
| `jarvis_project/pulse.py` | Autonomous background Cron-Agent ("The Pulse") + event triggers + unprompted Flash Tier speech |
| `jarvis_project/rag.py` | Local Document RAG ("Second Brain") — SQLite + `nomic-embed-text` embeddings |

### Non-Negotiable Hardware Rules (Never Break These)
- **Flash Tier (`qwen2.5:3b`):** MUST run fully on the GPU (`options={"num_gpu": -1}`) and stay resident (`keep_alive=-1`) for the whole session — it is the always-on conversation brain inside the 4 GB VRAM.
- **Pro Tier (`qwen3-coder:30b`, via `ask_pro_coder`):** MUST run on CPU only (`options={"num_gpu": 0}`) and unload after use (`keep_alive=0`) so it "goes back to sleep" in the 32 GB system RAM.
- **Vision Tier (`gemma4:e4b`, via `capture_and_analyze_screen`):** MUST unload after every screen analysis (`keep_alive=0`) so it never holds VRAM the Flash Tier needs.
- `faster-whisper` must always use `device="cpu"` and `compute_type="int8"`.
- Piper and pyttsx3 must always run on CPU.
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
| LLM + Tools | ✅ Working | qwen2.5:3b (Flash), 28 tools, GPU-pinned; tool loop smoke-tested (commit `58f30a8`) |
| The Pulse (Cron-Agent) | ✅ Working | Autonomous secondary daemon thread (`pulse.py`), event triggers (models, hardware, daily briefing, reminders) + Flash unprompted speech |
| Weather | ⚠️ Uncommitted | `get_weather` tool (wttr.in) added by another agent; deliberately kept OUT of commit `58f30a8` — needs review/commit |
| Memory | ✅ Working | SQLite, facts + conversation history + reminders |
| Self-Modify | ✅ Working | read/apply/restore with backup |
| Text Mode | ✅ Working | `python main.py --text` smoke-tested (no audio deps, no input-mode prompt) |
| Screen Vision | ⚠️ Model not pulled | `gemma4:e4b` code path wired with `keep_alive=0`; fails gracefully (404) until pulled |
| Pro Tier | ⚠️ Model not pulled | `qwen3-coder:30b` CPU + `keep_alive=0` code path wired; fails gracefully (404) until pulled |
| Web Search | ✅ Working | Playwright (Chromium) |
| File Executor | ✅ Working | `read_local_file` + `write_local_file` (Y/N confirm, blocks credentials/protected dirs) |
| Local RAG | ✅ Working | `index_documents` + `search_documents`; `nomic-embed-text` + `pypdf` installed |
| Confirmed Commands | ✅ Working | `confirm_and_run_command` — PowerShell, manual Y/N keystroke before execution |
| System Diagnosis | ✅ Working | `get_top_consumers` — top CPU/RAM processes via psutil for fan/slow-down diagnosis |
| Local Smart Home | ✅ Working | `control_home_assistant` — local Home Assistant REST API, bypasses cloud; requires `JARVIS_HA_TOKEN` env var |

---

## Active Priorities / Known Issues

> Update this section when you start or finish working on a priority item.

- [x] Autonomous Proactivity & Background Cron-Agent (The "Pulse") implemented and verified.
- [x] Pull the local embedding model: `ollama pull nomic-embed-text` (274 MB) — DONE, powers the RAG knowledge base.
- [ ] Pull the remaining tier models: `ollama pull qwen3-coder:30b` (~19 GB) and `ollama pull gemma4:e4b`. Code paths are already wired; they fail gracefully (404) until pulled.
- [ ] Review & commit the uncommitted `get_weather` feature in `jarvis_project/llm.py` + `tools.py` (added by another agent after commit `58f30a8`).
- [ ] Conversation history in `jarvis_memory.db` is full of junk (repeated "Hello"/"and" turns and stale "model not found" errors). Clear it with `memory.clear_history()` or by telling JARVIS "forget".
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

### [2026-08-15] — Kilo (kilo-auto/free)
**Files changed:** `jarvis_project/tools.py`, `jarvis_project/llm.py`, `plan.md` *(this file)*
**What:** Added two new local-only tools. (1) **System Resource Manager**: `get_top_consumers(limit=5)` uses `psutil` to enumerate running processes and returns the top CPU and RAM consumers with PIDs and percentages, enabling diagnosis of fan noise and system slowdowns. (2) **Local Smart Home Integration**: `control_home_assistant(service, entity_id, service_data=None)` hits the local Home Assistant REST API (`/api/services/<domain>/<service>`) using `JARVIS_HA_URL` and `JARVIS_HA_TOKEN` environment variables, bypassing cloud services entirely. Refuses to run if the token is unset. Both tools were registered in `llm.py` (`available_tools` + `_dispatch_tool`) and the system prompt was updated to guide the Flash tier to use them for system-diagnosis and local-device-control queries.
**Why:** User requested local environment control features aligned with JARVIS's zero-cloud philosophy: diagnosing system resource usage locally via psutil, and controlling smart home devices via the local Home Assistant API instead of cloud services like Alexa or Google Home.
**Notes:** Smoke-tested in the project `.venv`: `get_top_consumers` returns live process data; `control_home_assistant` correctly refuses when `JARVIS_HA_TOKEN` is missing. Both `tools.py` and `llm.py` pass `py_compile`. Tool count increased from 26 to 28.

---

### [2026-08-15] — Antigravity (Gemini 3.7 Flash)
**Files changed:** `jarvis_project/pulse.py` *(new)*, `jarvis_project/memory.py`, `jarvis_project/tools.py`, `jarvis_project/llm.py`, `jarvis_project/main.py`, `plan.md` *(this file)*
**What:** Implemented the autonomous background Cron-Agent (The "Pulse").
1. **Background Cron-Agent (`pulse.py`)**: Runs in a secondary daemon thread (`PulseEngine`) ticking quietly every few seconds with near-zero CPU footprint. Includes thread-safe `TurnCoordinator` to avoid overlapping audio or Ollama VRAM contention with user speech turns.
2. **Event-Driven Triggers**:
   - `ModelDownloadTrigger`: Watches for completed Ollama model downloads (`ollama.list()`), identifies model tiers (`qwen3-coder:30b` Pro Tier, `gemma4:e4b` Vision Tier, `nomic-embed-text` Embeddings), and initiates an announcement once per model.
   - `HardwareSpikeTrigger`: Monitors CPU/GPU temperature, sustained CPU load (>92%), memory pressure (>92%), and low disk space (<5 GB) with top-consumer diagnosis and 10-minute cooldown hysteresis.
   - `DailyBriefingTrigger`: Reads Tony Stark's daily morning briefing at 8:00 AM (customizable via `set_daily_briefing_time`) compiling live weather, date/time, hardware status, and pending tasks.
   - `ReminderTrigger`: Manages persistent SQLite reminders and alarms (`memory.py`).
3. **Flash Tier Unprompted Speech (`generate_unprompted_speech`)**: Triggers the GPU-pinned Flash Tier (`qwen2.5:3b`) to dynamically craft in-character spoken lines for background events, delivers them through `tts.speak` or console print, and synchronizes memory history.
4. **Tools & Orchestrator Integration**: Added `schedule_reminder`, `get_pulse_status`, `set_daily_briefing_time`, `trigger_daily_briefing` tools into `tools.py` and `llm.py`. Replaced legacy `_monitor_system` in `main.py` with `PulseEngine`.
**Why:** User requested "2. Proactivity & Automation (The 'Pulse')" to transition JARVIS from purely reactive to an autonomous assistant operating in the background.
**Notes:** Fully smoke-tested end-to-end: Flash Tier unprompted generation for model pulls, hardware spikes, daily briefings, and real-time background reminder execution verified.

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** `jarvis_project/llm.py`, `plan.md` *(this file)*
**What:** Rewrote `_build_system_prompt()` around a "smart friend" philosophy: (1) DO EXACTLY WHAT IS ASKED — no extra tools, no invented subtasks, ask one clarifying question when ambiguous; (2) truthful answers only from real tool output; (3) do NOT call tools for what the model already knows (added a concrete `2+2 → just say 4` example after the model repeatedly fired `run_cmd('1 + 2')` for simple arithmetic); (4) after a task, optionally suggest ONE useful next step in a single short sentence (e.g. cleanup after low disk space), but never nag and no generic "anything else?" taglines; (5) kept all existing tool routing (pulse, home assistant, system diagnosis, RAG, files, commands, memory, pro tier) but reorganized into a compact "when to use tools" list. Retained the earlier code-block guard (`_strip_code_fences` + one re-prompt) and the "never guess numbers" rule.
**Why:** User asked to make JARVIS "smarter" — do only what is asked and suggest follow-ups like a super smart friend, rather than dumping scripts, guessing numbers, or over-triggering tools.
**Notes:** Verified live through the tool loop: "What's 2 plus 2?" → just "4" (no tool); "Check my drive space." → `check_disk_space` with real numbers + one-line tip; "Open YouTube." → short; "Tell me a short fun fact." → trivia told from knowledge (no recall_facts/search). Minor residual: the small model still occasionally appends a generic "How else can I assist you?" tagline on chat answers — harmless, accepted. Not committed.

---

### [2026-08-16] — Antigravity (Gemini)
**Files changed:** `swarm/*` *(new)*, `.agents/rules/ponytail.md` *(new)*, `plan.md` *(this file)*
**What:** Built and deployed the **4-Agent Hybrid CLI Swarm & Ponytail Architecture**:
1. **Ponytail Integration**: Deployed `ponytail.md` rules and global plugin to enforce YAGNI, standard library first, native platform features, and minimal code diffs across all sessions.
2. **4-Agent Swarm Orchestrator**:
   - `swarm/start_swarm.ps1`: Automated launcher opening a 2x2 split grid in Windows Terminal (`wt.exe`) with isolated Git Worktrees (`Jarvis-backend`, `Jarvis-frontend`, `Jarvis-qa`).
   - `swarm/dispatch.py`: Natural language task refinery and dispatcher.
   - `swarm/tasks.json` & `swarm/swarm_helper.py`: Shared blackboard state coordination and CLI manager.
   - `swarm/worker.py`: Autonomous zero-touch watcher daemons with automatic token exhaustion / failure fallback to `agy`.
3. **Branching**: Created and published the dedicated branch `manual-upgrade-ai-swarm` to GitHub (`origin`).
**Why:** Enables multi-agent parallel software development on the Jarvis codebase across `agy`, `opencode`, `cline`, and `kilo` without file conflicts or manual context switching.
**Notes:** Verified end-to-end with live autonomous dispatch runs and clean Git worktree synchronization.

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** `jarvis_project/llm.py`, `plan.md` *(this file)*
**What:** Fixed a Flash Tier reliability bug found during a live voice session: `qwen2.5:3b` answered disk-space queries ("Check my drive") with a hallucinated Python script inside a code block ("I will execute this script now...") instead of calling `check_disk_space` — the tool loop returned that text instantly because it never produced a `tool_call`. Fixes: (1) added `_strip_code_fences()` — the loop now re-prompts the model ONCE when a plain-text answer contains a code fence (forcing a real tool call), and strips any remaining code fences from the final output before it reaches TTS/console; (2) hardened the system prompt — "NEVER report disk/CPU/RAM/GPU numbers unless a tool returned them — call `check_disk_space`/`get_system_stats` FIRST, never guess", and removed the hardcoded "42 GB free" example from the acknowledgment line (the model was parroting that exact number when it skipped the tool).
**Why:** A voice assistant that responds to "check my drive" with a code block and a fake promise to execute it is useless and alarming; TTS would literally read Python source aloud. The small model needs a guardrail because it sometimes skips tool calls entirely.
**Notes:** Verified live through the tool loop after the fix: "Check my drive see" → `check_disk_space` → real numbers (222.1 GB total, 9.7 GB free); "How much free space do I have on C" → correct; "What is eating my CPU" → `get_top_consumers`; garbled "Hit it or with" → asks for clarification. Not committed. NOTE: `llm.py` has since grown to ~840 lines (22+ tools) — other agents added Pulse tools (`schedule_reminder`, `get_pulse_status`, `set_daily_briefing_time`, `trigger_daily_briefing`), system-diagnosis tools, and `control_home_assistant`; this fix preserves all of them.

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** `jarvis_project/rag.py` *(new)*, `jarvis_project/tools.py`, `jarvis_project/llm.py`, `plan.md` *(this file)*
**What:** Implemented the three requested capabilities. (1) **Local File Executor**: `read_local_file(path)` (refuses credentials like `.env`/`*.key`, refuses binary, truncates at 200KB) and `write_local_file(path, content)` (always asks for a Y/N keystroke, blocks writes into `.venv`/`.git`/`.jarvis_backups`/`voices`, 500KB cap). (2) **Local Document RAG "Second Brain"**: new `rag.py` — SQLite (`jarvis_rag.db`), embeddings via `ollama.embeddings(model="nomic-embed-text")` (274 MB model pulled), chunking ~500 chars / 50 overlap, brute-force cosine search; `index_documents(folder)` + `search_documents(query, top_k)` tools; `.txt/.md/.py/.json/.csv` native and `.pdf` via `pypdf` (installed into venv). (3) **Safe Command Execution**: `confirm_and_run_command(command)` — prints the exact command, blocks until the user types 'y' at the console, 60s timeout, output capped at 8000 chars. All five tools were added to `llm.py` (`available_tools` + `_dispatch_tool` + system-prompt guidance) and registered end-to-end. Added `_normalize_path()` to fix a model habit of emitting drive paths as `\M\coding\...` instead of `M:\coding\...`.
**Why:** User asked for local file read/write, a local searchable document knowledge base (no cloud embeddings), and command execution gated by an explicit manual Y/N keystroke so the LLM can never run a powerful command without the user physically approving it.
**Notes:** 13/13 unit checks passed (refusals, confirms, roundtrip, index/search) plus a live Flash-tier test where `qwen2.5:3b` successfully read `plan.md` via `read_local_file`. The small model occasionally fumbles `search_documents` (once tried `index_documents` on a hallucinated path) — safe (fails with "not a directory") but worth a prompt tweak if it recurs. CONFLICT WARNING: another agent overwrote `tools.py` with an 18-line broken stub at 18:42; it was restored from `.jarvis_backups/20260815_184243_345815_tools.py` (which preserved `get_weather` + tier config + `import rag`) before adding the new functions. `nomic-embed-text` and `pypdf` are now installed. Not committed.

---

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** `jarvis_project/llm.py`, `jarvis_project/tools.py`, `jarvis_project/main.py`, `AGENTS.md`, `plan.md` *(this file)*
**What:** Brought the codebase in line with the final 3-tier architecture spec. `llm.py`: pinned the Flash Tier (`qwen2.5:3b`) fully to the GPU (`num_gpu=-1`) with permanent residency (`keep_alive=-1`), fixed the stale "phi4-mini" docstring. `tools.py`: Pro Tier (`qwen3-coder:30b`) now runs CPU-only (`num_gpu=0`) and unloads after use (`keep_alive=0`); Vision Tier (`gemma4:e4b`) unloads after every screen analysis (`keep_alive=0`). `main.py`: `--text` mode no longer prompts for an audio input mode. Rewrote `AGENTS.md` to document the 3-tier router, the scrapped sandbox loop, and the current 8-file layout.
**Why:** The spec's core hardware-split rules (flash resident in VRAM, pro/vision sleep between calls) were not enforced by the code — models stayed hot in RAM/VRAM and the flash model could be evicted. Enforcing the sleep/wake contract keeps VRAM locked for the real-time voice loop.
**Notes:** Committed as `58f30a8`. `qwen3-coder:30b` and `gemma4:e4b` are NOT installed on this machine yet — pull them before first use (see Active Priorities). The sandbox/self-evolve files were already deleted in commit `bd433e4`; do not reintroduce. NOTE: a `get_weather` feature appeared in `llm.py`/`tools.py` after this work was done and was deliberately left OUT of the commit (see Active Priorities).

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** *(none — verification only)* `plan.md` *(this file)*
**What:** Smoke-tested the whole stack after commit `58f30a8`. Verified: memory add/recall/delete facts; `get_system_stats`, `check_disk_space`, `run_cmd` safelist + blocklist refusals; Flash tier tool loop calling `check_disk_space` and returning a spoken-style answer; `main.py --text` greeting → LLM answer → graceful exit; `get_weather('New York')` returns live data via wttr.in. Confirmed Pro Tier and Vision Tier fail gracefully (404 "model not found") because the models aren't pulled yet.
**Why:** Confirm the 3-tier sleep/wake contract didn't break anything and establish a verified baseline.
**Notes:** Discovered the uncommitted `get_weather` feature in the working tree (not authored by this agent) — flagged in Active Priorities. Also found the conversation DB is cluttered with junk turns and stale 404 errors — flagged for cleanup. The Flash model routes weather questions to `jarvis_search` rather than the new `get_weather` tool; not a bug, but worth checking the tool descriptions if the weather routing should change.

---

### [2026-08-14] — Antigravity (Gemini)
**Files changed:** `plan.md` *(this file — created)*
**What:** Created `plan.md` as the mandatory shared context and change-log document for all agents working on the Jarvis codebase.
**Why:** Establishes a coordination layer so that multiple agents can work on the codebase without stepping on each other, and so any new agent can instantly understand the project state and history without having to reverse-engineer the code from scratch.
**Notes:** The current codebase is in a stable, working state. All modules are present. No bugs were known at the time of creation. Future agents should update the **Active Priorities** section before starting work and log their changes here when done.

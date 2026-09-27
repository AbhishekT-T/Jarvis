# JARVIS — Shared Multi-Agent Task Board & Plan

> **MANDATORY DIRECTIVE FOR ALL AGENTS:**  
> 1. Read this file in full along with [agents.md](file:///m:/coding/Jarvis/agents.md), [ARCHITECTURE.md](file:///m:/coding/Jarvis/ARCHITECTURE.md), and [MULTI_AGENT_PROTOCOL.md](file:///m:/coding/Jarvis/MULTI_AGENT_PROTOCOL.md) before writing any code.  
> 2. Claim your task in the **Active Task Board** below and lock your target files before making edits.  
> 3. After completing work and running verification tests, mark your task `[DONE]` and append an entry to the **Change Log** at the bottom of this file.

---

## 1. Project Overview & Quick Reference

**JARVIS** is a modular, zero-cloud voice and desktop AI assistant running locally on Windows 11.

- **GPU (GTX 1660 4GB):** Reserved exclusively for Ollama Flash Tier (`qwen2.5:3b`, `num_gpu=-1`, `keep_alive=-1`).
- **CPU & RAM (Ryzen 2700X, 32GB RAM):** Powers STT (`faster-whisper`), TTS (`Piper`), VAD, Wake Word, and on-demand Pro Tier (`qwen3-coder:30b`, `keep_alive=0`).
- **Virtual Environment:** Always use `jarvis_project/.venv`. Never create new virtual environments.

---

## 2. Active Multi-Agent Task Board (Blackboard)

Agents coordinate in real time using this board. When claiming a task, set status to `[CLAIMED: <AgentName>]`. When finished, set to `[DONE]`.

| Task ID | Task Description | Target Files | Domain Role | Status |
| :--- | :--- | :--- | :--- | :---: |
| **TASK-01** | Replace Playwright search with `duckduckgo_search` (`ddgs`) | `jarvis_project/tools.py` | ⚡ Tool Agent | `[READY]` |
| **TASK-02** | Eliminate `temp.wav` disk I/O in STT (pass in-memory float32 ndarray) | `jarvis_project/stt.py` | 🔊 Audio Agent | `[READY]` |
| **TASK-03** | Fix headless `input()` lock in GUI mode (`execute_admin_fix`, etc.) | `jarvis_project/tools.py` | ⚡ Tool Agent | `[READY]` |
| **TASK-04** | Replace PowerShell WinRT OCR with `winsdk` / in-process OCR | `jarvis_project/tools.py` | ⚡ Tool Agent | `[READY]` |
| **TASK-05** | Enable SQLite WAL mode & busy timeout for concurrency | `memory.py`, `rag.py` | 💾 Memory Agent | `[READY]` |
| **TASK-06** | Optimize RAG search using `sqlite-vec` or `chromadb` index | `jarvis_project/rag.py` | 💾 Memory Agent | `[READY]` |
| **TASK-07** | Replace bespoke trigger loop in `pulse.py` with `APScheduler` | `jarvis_project/pulse.py` | 💾 Memory Agent | `[READY]` |
| **TASK-08** | Replace `nvidia-smi` subprocess queries with `pynvml` | `tools.py`, `gui_server.py` | ⚡ Tool Agent | `[READY]` |
| **TASK-09** | Remove deprecated patch scripts (`patch_llm.py`, etc.) | Root directory | 🛡️ QA Agent | `[READY]` |

---

## 3. Subsystem Health Matrix

| Area | Component | Status | Notes |
| :--- | :--- | :---: | :--- |
| **Wake Word** | `wakeword.py` | ✅ Operational | `hey_jarvis.onnx` via openWakeWord. |
| **STT** | `stt.py` | ✅ Operational | `faster-whisper` base.en, CPU int8. Ready for in-memory ndarray upgrade. |
| **TTS** | `tts.py` | ✅ Operational | Piper (`en_GB-alan-medium`) with barge-in support. |
| **Flash Router** | `llm.py` | ✅ Operational | `qwen2.5:3b`, GPU-pinned, 35+ tools registered with tool callback hook. |
| **Pro Coder** | `tools.py` | ⚠️ Model unpulled | `qwen3-coder:30b`, CPU-only, `keep_alive=0`. Code wired; 404 until pulled. |
| **Vision Tier** | `tools.py` | ⚠️ Model unpulled | `gemma4:e4b`, multimodal screen analyzer. Code wired; 404 until pulled. |
| **Desktop HUD** | `gui_server.py`, `gui/*` | ✅ Operational | Cyberpunk HUD on `127.0.0.1:8765` with live telemetry & chat feed. |
| **VoiceOS** | `window_context.py` | ✅ Operational | Active foreground window inspection & context-aware dictation. |
| **Pulse Agent** | `pulse.py` | ✅ Operational | Secondary daemon thread, hardware/model triggers, unprompted Flash speech. |
| **Second Brain** | `rag.py` | ✅ Operational | Document chunking and embedding via `nomic-embed-text`. |
| **Memory** | `memory.py` | ✅ Operational | Persistent SQLite history, facts, and scheduled reminders. |

---

## 4. Change Log

Entries are listed in reverse-chronological order (newest first).

```
Template:
### [YYYY-MM-DD] — [Agent Name / Model]
**Files changed:** `file1.py`, `file2.py`
**What:** Short description of what was done.
**Why:** Reason — what problem it solved or feature it added.
**Notes:** Anything the next agent needs to know (gotchas, follow-up work, etc.)
```

### [2026-09-27] — Antigravity (Gemini)
**Files changed:** `agents.md`, `ARCHITECTURE.md` *(new)*, `MULTI_AGENT_PROTOCOL.md` *(new)*, `plan.md` *(this file)*  
**What:** Established complete Multi-Agent Governance & Collaboration Framework:
1. **`agents.md`**: Fully modernized to reflect 35+ tools, desktop HUD GUI, VoiceOS, Pulse engine, role ownership matrices, and non-negotiable hardware residency invariants.
2. **`ARCHITECTURE.md`**: Formalized inter-module technical contracts, 3-tier Ollama invocation contracts, REST API schemas, database schemas, and concurrency rules.
3. **`MULTI_AGENT_PROTOCOL.md`**: Formulated swarm collaboration rules, Git worktree isolation procedures, task claim and file-locking protocols, and verification gates.
4. **`plan.md`**: Upgraded into a real-time task blackboard tracking active tasks (`TASK-01` to `TASK-09`) with clear ownership and claim states.  
**Why:** Provides clear, enforceable documentation so multiple agents can work in parallel without stepping on each other's code, breaking API contracts, or corrupting state.  
**Notes:** All documentation matches the latest audited codebase state.

---

### [2026-09-17] — Antigravity (Gemini)
**Files changed:** `jarvis_project/gui/` *(new: index.html, gui.css, gui.js)*, `jarvis_project/gui_server.py` *(new)*, `jarvis_project/gui_launcher.py` *(new)*, `jarvis_project/main.py`, `jarvis_project/llm.py`, `run_jarvis.ps1`, `test_gui.py` *(new)*, `plan.md` *(this file)*  
**What:** Designed, built, and verified the **Cyberpunk Desktop HUD GUI**:
1. **Frontend HUD Interface**: Built a futuristic Stark/Iron-Man style HUD with real-time hardware telemetry pills (CPU, RAM, GPU VRAM, active foreground focus via `window_context`), 60 FPS HTML5 canvas holographic Arc Reactor & dynamic audio soundwave visualizer, interactive chat feed with expandable tool execution chips, Push-to-Talk button, text query bar, and quick action buttons.
2. **Local GUI Server**: Multithreaded standard-library HTTP server on `127.0.0.1:8765` (`gui_server.py`) serving frontend assets and REST API endpoints (`/api/status`, `/api/history`, `/api/chat`, `/api/trigger_listen`).
3. **Desktop App Window Launcher**: `gui_launcher.py` launches Edge/Chrome in standalone App Mode (`--app=http://127.0.0.1:8765`), providing a dedicated, borderless, frameless desktop application with zero heavy dependencies (Electron/Qt not needed).
4. **Integration**: Added `tool_execution_callback` hook in `llm.py` to capture real-time tool execution outputs for the HUD; added `--gui` support to `main.py` and `-Gui` flag to `run_jarvis.ps1`.
5. **Testing**: Implemented `test_gui.py` testing static asset delivery, telemetry APIs, interactive chat, and live tool capture end-to-end. All tests passed.  
**Why:** User requested a full working GUI for JARVIS.  
**Notes:** 100% test pass rate across `test_gui.py` and `test_voiceos.py`.

---

### [2026-08-27] — Antigravity (Gemini)
**Files changed:** `jarvis_project/window_context.py` *(new)*, `jarvis_project/main.py`, `jarvis_project/stt.py`, `jarvis_project/tools.py`, `jarvis_project/llm.py`, `plan.md` *(this file)*  
**What:** Implemented the complete 4-Layer VoiceOS "Thought-to-Action" Architecture:
1. **Layer 1 — Active Window Detection & Context-Aware Dictation**: Added `window_context.py` (Win32 foreground window & process inspection, app category heuristics for coding, chat, email, docs, terminal, browsers), `format_dictation_for_app()`, and `type_into_active_window()` with clipboard preservation. Registered `dictate_into_active_window` and `get_active_window_info`.
2. **Layer 2 — Universal Global Push-to-Talk Hotkey**: Added Mode `[5] VoiceOS` in `main.py` listening globally on `F8` (`VOICEOS_KEY`) across the entire OS without modifier key collisions; added stream flush delay in `stt.py` to prevent clipping the final spoken syllable.
3. **Layer 3 — Edit & Ask Mode**: Added `get_selected_text()` (Ctrl+C capture with clipboard rollback + terminal SIGINT safety check) and `edit_selected_text()` (in-place text transformation/rewriting via GPU-pinned Flash Tier).
4. **Layer 4 — Agent Mode (Email & Calendar Scheduling)**: Added `draft_email()` (`mailto:` composer + clipboard copy), `schedule_calendar_event()` (.ics file generation + default calendar handler + persistent reminder tracking), and `list_calendar_events()` with mandatory physical `[Y/N]` confirmation prompts.  
**Why:** Transitions JARVIS from a conversational voice chatbot into a system-wide thought-to-action AI layer, matching commercial VoiceOS workflows while maintaining strict local execution and safety guarantees.  
**Notes:** Verified all files compile cleanly with `py_compile`. Tool count increased to 35. Fully backward-compatible with existing modes (1-4) and Flash Tier residency rules.

---

### [2026-08-15] — Kilo (kilo-auto/free)
**Files changed:** `jarvis_project/tools.py`, `jarvis_project/llm.py`, `plan.md` *(this file)*  
**What:** Added two new local-only tools: (1) `get_top_consumers(limit=5)` using `psutil` to diagnose fan noise and CPU/RAM slowdowns; (2) `control_home_assistant(service, entity_id, service_data=None)` hitting local Home Assistant REST API.  
**Why:** User requested local environment control features aligned with JARVIS's zero-cloud philosophy.  
**Notes:** Tool count increased from 26 to 28.

---

### [2026-08-15] — Antigravity (Gemini 3.7 Flash)
**Files changed:** `jarvis_project/pulse.py` *(new)*, `jarvis_project/memory.py`, `jarvis_project/tools.py`, `jarvis_project/llm.py`, `jarvis_project/main.py`, `plan.md` *(this file)*  
**What:** Implemented the autonomous background Cron-Agent (The "Pulse"). Added `PulseEngine` secondary thread with thread-safe `TurnCoordinator`, triggers for model pulls, hardware spikes, daily briefings, and reminders with unprompted Flash speech.  
**Why:** Transitioned JARVIS from purely reactive to an autonomous assistant operating in the background.  
**Notes:** Fully smoke-tested end-to-end.

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** `jarvis_project/llm.py`, `plan.md` *(this file)*  
**What:** Rewrote `_build_system_prompt()` around a "smart friend" philosophy: do exactly what is asked, truthful tool output only, never guess numbers, and optional concise next steps.  
**Why:** User asked to make JARVIS do only what is asked and avoid over-triggering tools.  
**Notes:** Verified live through tool loop.

---

### [2026-08-16] — Antigravity (Gemini)
**Files changed:** `swarm/*` *(new)*, `.agents/rules/ponytail.md` *(new)*, `plan.md` *(this file)*  
**What:** Deployed Ponytail integration and Swarm coordination scripts on dedicated branch `manual-upgrade-ai-swarm`.  
**Why:** Enables multi-agent parallel software development without file conflicts.  
**Notes:** Verified end-to-end.

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** `jarvis_project/llm.py`, `plan.md` *(this file)*  
**What:** Fixed Flash Tier tool-call skipping by adding `_strip_code_fences()` and re-prompt guardrails when the model outputs code blocks instead of calling tools.  
**Why:** Prevented Python code blocks from being spoken aloud by TTS.  
**Notes:** Verified live through tool loop.

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** `jarvis_project/rag.py` *(new)*, `jarvis_project/tools.py`, `jarvis_project/llm.py`, `plan.md` *(this file)*  
**What:** Implemented Local File Executor (`read_local_file`, `write_local_file`), Local Document RAG (`rag.py`), and `confirm_and_run_command`.  
**Why:** User requested local file access, searchable local knowledge base, and manual confirmation for system commands.  
**Notes:** Unit checks passed.

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** `jarvis_project/llm.py`, `jarvis_project/tools.py`, `jarvis_project/main.py`, `AGENTS.md`, `plan.md` *(this file)*  
**What:** Brought the codebase in line with the final 3-tier architecture spec: pinned Flash Tier to GPU, enforced CPU-only sleep/wake on Pro and Vision tiers.  
**Why:** Enforcing the sleep/wake contract keeps VRAM locked for the real-time voice loop.  
**Notes:** Committed as `58f30a8`.

---

### [2026-08-15] — big-pickle (opencode)
**Files changed:** *(none — verification only)* `plan.md` *(this file)*  
**What:** Smoke-tested the entire stack after commit `58f30a8`.  
**Why:** Confirmed 3-tier sleep/wake contract didn't break anything.  
**Notes:** Baseline verified.

---

### [2026-08-14] — Antigravity (Gemini)
**Files changed:** `plan.md` *(created)*  
**What:** Created `plan.md` as the mandatory shared context and change-log document for all agents working on the Jarvis codebase.  
**Why:** Establishes coordination layer so multiple agents work without stepping on each other.

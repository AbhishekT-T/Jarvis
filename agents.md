# AGENTS.md — Multi-Agent Engineering & Operations Manual

> **MANDATORY DIRECTIVE FOR ALL AI AGENTS & ASSISTANTS:**  
> You MUST read this document in its entirety along with [plan.md](file:///m:/coding/Jarvis/plan.md) and [ARCHITECTURE.md](file:///m:/coding/Jarvis/ARCHITECTURE.md) before inspecting, editing, or executing any code in this repository.  
> Every change must respect the hardware split, inter-module contracts, and multi-agent file ownership boundaries defined herein.

---

## 1. Project Mission & Identity

**JARVIS** is an entirely local, zero-cloud, modular voice and desktop AI assistant built on Windows 11. It operates with zero subscription costs, requires no external API keys, and runs continuous voice interaction, tool execution, operating system control, and background proactivity on local consumer hardware.

---

## 2. Hardware Constraints & The 3-Tier Split (Non-Negotiable)

The architecture is strictly engineered around hardware partitioning across GPU VRAM and CPU/RAM:

| Compute Tier | Model | Hardware Allocation | Residency & Parameters | Primary Role |
| :--- | :--- | :--- | :--- | :--- |
| **Flash Tier** (The Brain) | `qwen2.5:3b` | **GPU VRAM** (GTX 1660 4GB) | `num_gpu=-1`, `keep_alive=-1`<br>*(Locked resident in VRAM)* | Real-time voice loop (<400ms), general conversation, tool orchestration. |
| **Pro Tier** (Heavy Coder) | `qwen3-coder:30b` | **System RAM & CPU** (32GB RAM, Ryzen 2700X) | `num_gpu=0`, `keep_alive=0`<br>*(Unloads immediately after call)* | Complex software engineering, architectural logic, debugging via `ask_pro_coder`. |
| **Vision Tier** (Screen Inspector)| `gemma4:e4b` | **GPU VRAM / RAM** | `keep_alive=0`<br>*(Unloads immediately after call)* | Multimodal screen analysis via `capture_and_analyze_screen`. |

### Invariant Rules
1. **Never evict the Flash Tier:** The Flash Tier must stay resident (`keep_alive=-1`) in GPU VRAM for the entire session. Never set `keep_alive=0` on `qwen2.5:3b`.
2. **Never leave Pro or Vision tiers resident:** `ask_pro_coder` and `capture_and_analyze_screen` must enforce `keep_alive=0` so they release their memory immediately upon completion.
3. **Audio stack runs on CPU:** `faster-whisper` (`base.en`) MUST run with `device="cpu"` and `compute_type="int8"`. Piper TTS and pyttsx3 MUST run on CPU. Never offload STT/TTS to GPU.
4. **Environment Isolation:** Always execute using the project virtual environment at `jarvis_project/.venv`. Never create new virtual environments.

---

## 3. Multi-Agent Team Structure & File Ownership

To avoid merge collisions, race conditions, or broken contracts when multiple agents work simultaneously, the codebase is divided into clear functional domains with strict file ownership.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           MULTI-AGENT DOMAIN ROLES                              │
├─────────────────────┬───────────────────────────┬───────────────────────────────┤
│ 🧠 ORCHESTRATION    │ ⚡ OS & CAPABILITIES       │ 🔊 AUDIO & VOICEOS            │
│ Files: main.py,     │ Files: tools.py,          │ Files: stt.py, tts.py,        │
│        llm.py       │        window_context.py  │        vad.py, wakeword.py    │
├─────────────────────┼───────────────────────────┼───────────────────────────────┤
│ 🖥️ HUD & FRONTEND   │ 💾 MEMORY & RAG           │ 🛡️ QA & BENCHMARKING          │
│ Files: gui_server,  │ Files: memory.py,         │ Files: test_gui.py,           │
│        gui/*,       │        rag.py,            │        test_voiceos.py,       │
│        gui_launcher │        pulse.py           │        tier_smoke_test.py     │
└─────────────────────┴───────────────────────────┴───────────────────────────────┘
```

### 3.1 Role Definitions & Ownership Matrix

| Domain Role | Primary Files Owned | Permitted Modifications | Prohibited Actions |
| :--- | :--- | :--- | :--- |
| **🧠 Orchestration Agent** | `jarvis_project/main.py`<br>`jarvis_project/llm.py` | Event loop, system prompts, tool schema registration (`available_tools`), `_dispatch_tool()`, multi-round reasoning. | Modifying audio capture logic directly; altering tool implementations in `tools.py`. |
| **⚡ OS & Tool Agent** | `jarvis_project/tools.py`<br>`jarvis_project/window_context.py` | Tool implementations, Win32 automation, OS telemetry, process inspection, external integrations. | Changing tool schemas in `llm.py` without updating `available_tools` in sync; bypassing `TurnCoordinator`. |
| **🔊 Audio & VoiceOS Agent**| `jarvis_project/stt.py`<br>`jarvis_project/tts.py`<br>`jarvis_project/vad.py`<br>`jarvis_project/wakeword.py`| Audio capture, VAD thresholding, Whisper transcription, Piper speech synthesis, barge-in detection. | Importing `vad.py` outside of `stt.py` and `tts.py`; routing audio processing to GPU. |
| **🖥️ HUD & Frontend Agent** | `jarvis_project/gui_server.py`<br>`jarvis_project/gui_launcher.py`<br>`jarvis_project/gui/*` | Cyberpunk HUD UI (`index.html`, `gui.css`, `gui.js`), HTTP REST endpoints, status streaming. | Breaking REST schema contracts; modifying LLM tool execution logic. |
| **💾 Memory & Pulse Agent** | `jarvis_project/memory.py`<br>`jarvis_project/rag.py`<br>`jarvis_project/pulse.py` | SQLite schema, document indexing & embeddings, autonomous background triggers, unprompted speech events. | Running long blocking RAG searches on the main thread; bypassing `TurnCoordinator` during speech. |
| **🛡️ QA & Testing Agent** | `test_*.py`<br>`tier_smoke_test.py` | Automated tests, regression testing, concurrency benchmarking, telemetry verification. | Modifying production source code under `jarvis_project/` without an assigned task ticket. |

---

## 4. Multi-Agent Coordination & Concurrency Rules

### 4.1 The 5-Step Agent Workflow
Every agent engaging with this repository MUST execute the following sequence:

1. **Pre-Flight Orientation:**
   - Read [plan.md](file:///m:/coding/Jarvis/plan.md) to check active sprint priorities and locks.
   - Read [ARCHITECTURE.md](file:///m:/coding/Jarvis/ARCHITECTURE.md) to verify API/data contracts.
2. **Claim Task & File Lock:**
   - In [plan.md](file:///m:/coding/Jarvis/plan.md), locate the target task or register a new one.
   - Set status to `[CLAIMED: <AgentName>]` and list the locked files.
   - If an intended file is already claimed by another agent, DO NOT touch it. Work on a different task or coordinate.
3. **Execution & Ponytail Principles:**
   - Prefer standard libraries or established packages over reinventing the wheel (e.g. in-memory numpy in `faster_whisper`, `duckduckgo_search` over Playwright scraping, `pynvml` over `nvidia-smi` subprocesses).
   - Keep diffs surgical and minimal. Boring over clever.
4. **Mandatory Verification Gate:**
   - Compile all modified files with `python -m py_compile <file>`.
   - Run relevant unit tests:
     - VoiceOS / Win32: `python test_voiceos.py`
     - GUI Server: `python test_gui.py`
     - 3-Tier Architecture & Residency: `python tier_smoke_test.py`
5. **Post-Flight Logging:**
   - Append a standardized change log entry to [plan.md](file:///m:/coding/Jarvis/plan.md).
   - Release the file lock by marking the task `[DONE]`.

### 4.2 Cross-Module Synchronization Invariants
- **Tool Registration Symmetry:** Whenever a tool function is added or modified in `tools.py`, its schema MUST be updated in `llm.py:available_tools` and its handler dispatched in `llm.py:_dispatch_tool()`.
- **Audio Barge-In & Speech Locking:** Any background voice generation (such as Pulse unprompted alerts) MUST acquire `pulse.coordinator.acquire_pulse_turn()` before speaking to prevent colliding with active user speech.
- **Database Thread Safety:** Both `jarvis_memory.db` and `jarvis_rag.db` are accessed concurrently across HTTP threads, the main loop, and background Pulse threads. All connections MUST enable WAL mode and set busy timeouts:
  ```python
  conn.execute("PRAGMA journal_mode=WAL;")
  conn.execute("PRAGMA busy_timeout=5000;")
  ```
- **No Headless Blocking:** Never call `input()` inside functions that can be invoked via GUI or headless mode (`execute_admin_fix`, `confirm_and_run_command`, etc.).

---

## 5. Directory Structure & Map

```
m:\coding\Jarvis\
├── AGENTS.md                  # Master Agent Specification & Operating Manual (this file)
├── plan.md                    # Synchronized Multi-Agent Task Board & Change Log
├── ARCHITECTURE.md            # System Contracts, API Schemas & Data Flow
├── MULTI_AGENT_PROTOCOL.md    # Swarm Execution Rules, Git Worktrees & Locks
├── CODEBASE_EXPLAINED.md      # Detailed line-by-line code explanation
├── WORKFLOW_AND_SYSTEM_AUDIT.md # Technical audit & vulnerability matrix
├── run_jarvis.ps1             # PowerShell launcher (-Text, -Gui, or default Voice)
├── JARVIS.exe / launcher.cs   # Silent C# desktop bootstrap executable
├── tier_smoke_test.py         # Hardware residency & 3-tier contract test
├── test_voiceos.py            # Win32 context inspection & dictation test
├── test_gui.py                # HUD HTTP API and telemetry test
│
└── jarvis_project/            # Core Python package (runs inside .venv)
    ├── main.py                # Master Orchestrator & CLI entry point
    ├── llm.py                 # Flash Tier cognitive router (35+ tools schema)
    ├── tools.py               # OS actions, Pro/Vision delegation, VoiceOS tools
    ├── window_context.py      # Win32 foreground window & process classification
    ├── stt.py                 # Faster-Whisper CPU int8 transcription
    ├── tts.py                 # Piper neural TTS with barge-in support
    ├── vad.py                 # Voice activity detection & speech windowing
    ├── wakeword.py            # openWakeWord ONNX "Hey Jarvis" detector
    ├── memory.py              # SQLite conversation history, facts & reminders
    ├── pulse.py               # Autonomous background Cron-Agent & unprompted speech
    ├── rag.py                 # Local Document RAG (SQLite + nomic-embed-text)
    ├── vault.py               # Environment variable & token loader (.env)
    ├── gui_launcher.py        # Desktop App window lifecycle manager
    ├── gui_server.py          # Multithreaded HUD HTTP REST API server
    └── gui/                   # Desktop Cyberpunk HUD Frontend
        ├── index.html         # HUD layout, canvas Arc Reactor visualizer
        ├── gui.css            # Futuristic glassmorphism styling
        └── gui.js             # Real-time telemetry poller, chat & audio bus
```

---

## 6. Verification & Quality Gates

Before declaring any task complete or committing changes, run the appropriate gate commands:

```powershell
# 1. Syntax & Bytecode Compilation Check
& ".\jarvis_project\.venv\Scripts\python.exe" -m py_compile jarvis_project/*.py

# 2. GUI Server API & Static Asset Delivery Test
& ".\jarvis_project\.venv\Scripts\python.exe" test_gui.py

# 3. VoiceOS Active Window & Keystroke Synthesis Test
& ".\jarvis_project\.venv\Scripts\python.exe" test_voiceos.py

# 4. 3-Tier Hardware Split & Model Sleep/Wake Test
& ".\jarvis_project\.venv\Scripts\python.exe" tier_smoke_test.py

# 5. CLI Text Mode Smoke Test (Zero Audio Dependencies)
& ".\jarvis_project\.venv\Scripts\python.exe" jarvis_project/main.py --text
```

Agents must uphold these standards to keep JARVIS lean, reliable, and production-ready.

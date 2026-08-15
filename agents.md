# TASK: JARVIS — Local 3-Tier Voice Agent Orchestrator

## 1. Project Goal
Build a modular, zero-cost, local voice-controlled AI assistant ("JARVIS") in Python. The system runs continuous voice interaction, tool execution (OS control), and voice output locally on the specified hardware.

## 2. Hardware Constraints & Hardware-Split Strategy
- **GPU:** NVIDIA GTX 1660 (4GB VRAM). Reserved for Ollama — used by the **Flash Tier** (always-resident) and briefly by the **Vision Tier**.
- **CPU & RAM:** AMD Ryzen 7 2700X + 32GB RAM. Used by STT, TTS, VAD, the wake-word gatekeeper, and the **Pro Tier** (`qwen3-coder:30b`).

### Mandatory Rules (Never Break These)
1. **Flash Tier (`llm.py`):** `ollama` with `qwen2.5:3b`. Force full GPU offload with `options={"num_gpu": -1}` and keep resident with `keep_alive=-1` so it stays locked inside the 4GB VRAM for the whole session.
2. **Speech-to-Text (`stt.py`):** `faster-whisper` with model `"base.en"`. MUST force `device="cpu"` and `compute_type="int8"` to preserve GPU VRAM.
3. **Text-to-Speech (`tts.py`):** `Piper` (fallback `pyttsx3`) running strictly on the CPU.
4. **Pro Tier (`tools.py` → `ask_pro_coder`):** `qwen3-coder:30b`. MUST run on CPU only (`options={"num_gpu": 0}`) and unload after use (`keep_alive=0`) so it "goes back to sleep" and returns its RAM to the system.
5. **Vision Tier (`tools.py` → `capture_and_analyze_screen`):** `gemma4:e4b`. MUST unload after use (`keep_alive=0`) so it never holds VRAM the Flash Tier needs.
6. **Environment:** Use the existing `.venv` (at `jarvis_project/.venv`). Do not create new virtual environments.

---

## 3. The Final 3-Tier Architecture (Agent-as-a-Tool Router)

One lightweight always-on model acts as the brain and calls heavier specialized models only when necessary, through normal tool calls.

### Tier 1 — The "Flash" Tier (The Orchestrator)
- **Model:** `qwen2.5:3b`
- **Hardware State:** Locked entirely inside the 4GB GPU VRAM (`num_gpu=-1`, `keep_alive=-1`).
- **Use Cases:** Handles the real-time voice loop (STT → LLM → TTS) with zero latency. Casual conversation, triaging user requests, and orchestrating basic tools (web search, database memory, OS actions).

### Tier 2 — The "Pro" Tier (The Heavy Developer)
- **Model:** `qwen3-coder:30b` (via the `ask_pro_coder` tool).
- **Hardware State:** Sleeps until called; loads into the 32GB system RAM, runs off the Ryzen CPU, returns raw code to the Flash Tier, then unloads (`keep_alive=0`).
- **Use Cases:** Complex software development, multi-threaded Python scripts, deep architectural design, heavy logic debugging.

### Tier 3 — The "Vision" Tier (The Screen Analyzer)
- **Model:** `gemma4:e4b` (via the `capture_and_analyze_screen` tool; `describe_screen` uses Windows WinRT OCR as a lighter alternative).
- **Hardware State:** Loads on demand, uses `mss` to capture the desktop in memory, answers, then unloads (`keep_alive=0`).
- **Use Cases:** Reading error popups, inspecting UI elements, looking at code on screen without copy/paste.

### The Sandbox Evaluator Loop — DEPRECATED / SCRAPPED
The fully autonomous self-evolution loop (`sandbox_tools.py`, `self_evolve.py`, `demo_self_evolve.py`) was explored and then **scrapped to save hardware overhead**. Do NOT reintroduce it. The surviving safety mechanism is `apply_code_change()` in `tools.py`, which backs up, `py_compile`-validates, and rolls back JARVIS's own source edits.

---

## 4. Utility Sub-Agents (Background Toolsets)

- **The Live Data Agent (`jarvis_search`):** Playwright-based Google search. Overcomes local models' static training cutoffs by fetching real-time 2026 data before answering.
- **The Persistent Memory Agent (`remember_fact` / `recall_facts` / `forget_fact`):** Stores personal context (e.g. car mileage, hardware specs) in SQLite (`jarvis_memory.db`), giving JARVIS long-term memory across reboots. Conversation history is also persisted there.
- **The Wake Word Gatekeeper (`wakeword.py`):** openWakeWord (ONNX) offline trigger ("Hey Jarvis") with an ultra-low CPU footprint, so the mic loop never maxes out the Ryzen when idle. Also supports Push-to-Talk (hold CTRL) and Always-Listening (classic VAD) modes.

---

## 5. File Structure

```
jarvis_project/
 tools.py       # OS actions + Pro/Vision tier delegation + self-modification
 stt.py         # Microphone capture & faster-whisper CPU transcription
 tts.py         # Local CPU TTS (Piper) with barge-in; pyttsx3 fallback
 vad.py         # Voice-activity detection (UtteranceRecorder + barge-in monitor)
 wakeword.py    # openWakeWord "Hey Jarvis" gatekeeper (ONNX, CPU)
 memory.py      # SQLite persistent memory (history + facts)
 llm.py         # Flash Tier Ollama interface, 16 tool definitions, tool loop
 main.py        # Core Orchestrator event loop (voice loop, monitor thread, --text mode)
```

---

## 6. Detailed Component Specifications

### File 1: `tools.py`
Real-world actions with docstrings and type annotations so Ollama can parse them:
- `open_app(app_name)` — launches a Windows app or opens a website (PATH + Registry + standard-dir resolution; no shell, injection-safe).
- `get_system_stats()` — CPU, RAM, and NVIDIA GPU usage via `psutil` + `nvidia-smi`.
- `run_cmd(command)` — read-only PowerShell command with denylist + safelist.
- `jarvis_search(query)` — Google search via Playwright.
- `check_disk_space(drive)` — total/used/free for a drive.
- `install_app(app_name, force=False)` — winget install after a storage-space check.
- `describe_screen()` — screenshot + Windows WinRT OCR + active window title.
- `capture_and_analyze_screen(prompt)` — `mss` capture + Vision Tier (`gemma4:e4b`, `keep_alive=0`).
- `ask_pro_coder(prompt)` — delegates to Pro Tier (`qwen3-coder:30b`, CPU-only, `keep_alive=0`).
- Self-inspection/self-modification: `list_project_files`, `read_project_file`, `apply_code_change`, `restore_backup`.
- Memory delegators: `remember_fact`, `recall_facts`, `forget_fact` (→ `memory.py`).

### File 2: `stt.py`
`listen_and_transcribe()` records a full utterance (VAD, pause-detected) and transcribes with `WhisperModel("base.en", device="cpu", compute_type="int8")`. Lazy-cached model, gain normalization, optional `noisereduce`. `listen_and_transcribe_ptt(key)` for push-to-talk.

### File 3: `tts.py`
`speak(text)` synthesizes with Piper (`en_GB-alan-medium`) or pyttsx3 and plays via sounddevice. Supports barge-in: if the user starts speaking, playback aborts instantly and `True` is returned so the caller re-listens.

### File 4: `vad.py`
Shared audio primitives: `UtteranceRecorder` (start-to-end utterance capture for STT) and `SpeechInterruptMonitor` (barge-in detection for TTS). Only imported by `stt.py` and `tts.py`.

### File 5: `wakeword.py`
`WakeWordDetector` — openWakeWord ONNX model for "Hey Jarvis" (16kHz, mono, int16, 1280-sample chunks). Modes: wake-word only, combined with PTT, or classic always-listening.

### File 6: `memory.py`
SQLite (`jarvis_memory.db`): `history` table (last 20 turns for context) + `facts` table (long-term facts). Parameterized queries, defensive `init_db()` on import and per call.

### File 7: `llm.py`
`query_jarvis(prompt, history)`:
- Calls `ollama.chat(model=qwen2.5:3b, ..., options={"num_gpu": -1}, keep_alive=-1)` with the 16 available tools.
- Runs a multi-step tool loop (max 5 rounds): if Ollama returns `tool_calls`, executes the corresponding function in `tools.py` via `_dispatch_tool`, feeds the output back, and continues until a plain-text answer.
- Returns the final conversational text.

### File 8: `main.py`
Entry point:
- `--text` flag runs a text-only session (no audio imports).
- Interactive input-mode picker: wake word / PTT / combined / always-listening.
- Background `_monitor_system()` daemon thread (disk < 5GB, CPU > 90%, RAM > 90% alerts).
- `while True` loop: trigger → STT → memory → `llm.query_jarvis` → TTS (barge-in aware) → re-listen on interrupt.
- Graceful exit on "quit" / "exit" / "stop" / "goodbye"; memory wipe on "forget".

---

## 7. Setup Notes

- Pull the tier models with `ollama pull`: `qwen2.5:3b` (installed), `qwen3-coder:30b` (~19GB), `gemma4:e4b`.
- Run: `python main.py` from `jarvis_project/` using `.venv`. For text-only testing: `python main.py --text`.

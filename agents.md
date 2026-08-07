# TASK: Build the "JARVIS" Local Voice Agent Orchestrator

## 1. Project Goal
Build a modular, zero-cost, local voice-controlled AI assistant ("JARVIS") in Python. The system must run continuous voice interaction, tool execution (OS control), and voice output locally on specified hardware.

## 2. Hardware Constraints & Hardware-Split Strategy
- **GPU:** NVIDIA GTX 1660 (4GB VRAM). Reserved ENTIRELY for Ollama.
- **CPU & RAM:** AMD Ryzen 7 2700X + 32GB RAM. Reserved for STT and TTS engines.

### Mandatory Rules:
1. **LLM Engine:** Use `ollama` with `qwen2.5:3b` running on CUDA.
2. **Speech-to-Text (STT):** Use `faster-whisper` with model `"base.en"`. MUST force `device="cpu"` and `compute_type="int8"` to preserve GPU VRAM.
3. **Text-to-Speech (TTS):** Use `Piper` or `pyttsx3` running strictly on the CPU.
4. **Environment:** Use the existing Python virtual environment (`.venv`). Do not create new virtual environments.

---

## 3. Architecture & File Structure

Create the following file modular structure in `jarvis_project/`:

jarvis_project/
 tools.py       # OS-level execution functions (system stats, app opening, shell commands)
 stt.py         # Microphone capture & faster-whisper CPU transcription
 tts.py         # Local CPU text-to-speech output
 llm.py         # Ollama interface with function calling/tools
 main.py        # Core Orchestrator event loop

---

## 4. Detailed Component Specifications

### File 1: `tools.py`
Implement standard Python functions with clear docstrings and type annotations so Ollama can parse them as tools:
- `open_app(app_name: str)`: Launches a Windows application using `os.system` or `subprocess`.
- `get_system_stats()`: Uses `psutil` to return current CPU, RAM, and GPU usage.
- `run_cmd(command: str)`: Executes a powershell/cmd command and returns stdout/stderr.

### File 2: `stt.py`
- Class/Function `listen_and_transcribe()`:
  - Listens to the default microphone using `PyAudio` or `sounddevice`.
  - Saves temporary audio to `.wav`.
  - Transcribes using `WhisperModel("base.en", device="cpu", compute_type="int8")`.
  - Returns transcribed string.

### File 3: `tts.py`
- Function `speak(text: str)`:
  - Takes a string input and speaks it aloud using local CPU TTS without blocking the main thread where possible.

### File 4: `llm.py`
- Function `query_jarvis(prompt: str, history: list)`:
  - Calls `ollama.chat()` with model `qwen2.5:3b`.
  - Passes available tools from `tools.py`.
  - Checks if Ollama returned `tool_calls`.
  - If a tool call exists: executes the corresponding Python function in `tools.py`, feeds the output back to Ollama, and gets the final conversational response.
  - Returns the text response.

### File 5: `main.py`
- The main entry point:
  - Runs a clean `while True` loop:
    1. Prompt user / listen via `stt.py`.
    2. Send text to `llm.py`.
    3. Pass LLM output to `tts.py`.
  - Include graceful exit commands (e.g., "quit", "exit", "stop").

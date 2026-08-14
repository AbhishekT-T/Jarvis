# JARVIS — Complete Codebase Documentation

> A fully local, modular voice AI assistant. No cloud. No API keys. Runs 100% on your machine.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Data Flow](#data-flow)
3. [Technology Stack](#technology-stack)
4. [File: main.py](#file-mainpy--the-orchestrator)
5. [File: llm.py](#file-llmpy--the-llm-brain)
6. [File: tools.py](#file-toolspy--os-actions--capabilities)
7. [File: stt.py](#file-sttpy--speech-to-text)
8. [File: tts.py](#file-ttspy--text-to-speech)
9. [File: vad.py](#file-vadpy--voice-activity-detection)
10. [File: wakeword.py](#file-wakewordpy--wake-word-detection)
11. [File: memory.py](#file-memorypy--persistent-memory)
12. [File: sandbox_tools.py](#file-sandbox_toolspy--safe-code-execution)
13. [File: self_evolve.py](#file-self_evolvepy--autonomous-code-generation)
14. [File: demo_self_evolve.py](#file-demo_self_evolvepy--demo-runner)

---

## System Architecture

Every file has exactly one responsibility. They are wired together by `main.py`.

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                              │
│               (Master Conversation Loop)                    │
└──┬──────────┬──────────┬──────────┬──────────┬─────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
wakeword   stt.py     llm.py     tts.py    memory.py
  .py     (listen)   (think)    (speak)   (remember)
           │          │          │
           ▼          ▼          ▼
         vad.py    tools.py    vad.py
        (detect)  (act on OS) (barge-in)
                   │
                   ▼
            sandbox_tools.py
            (safe code exec)
                   ▲
            self_evolve.py
            (auto-debug AI)
                   ▲
          demo_self_evolve.py
              (demo runner)
```

---

## Data Flow

This is exactly what happens from the moment you speak to when JARVIS replies:

```
1. YOU SPEAK
      │
      ▼
2. wakeword.py  ──►  Detects "Hey Jarvis" (or CTRL key held)
      │
      ▼
3. stt.py  ──►  vad.py records your utterance  ──►  faster-whisper transcribes
      │
      ▼  (plain text: "Open YouTube")
4. main.py  ──►  memory.py appends your message to DB
      │
      ▼
5. llm.py  ──►  Builds messages (system prompt + history + your text)
               ──►  ollama.chat(qwen2.5:3b) on GPU
               ──►  Model returns tool_call: open_app("youtube")
               ──►  _dispatch_tool() → tools.py.open_app("youtube")
               ──►  Result fed back to model → final text answer
      │
      ▼  (text: "Opening YouTube now, sir.")
6. main.py  ──►  memory.py appends JARVIS's response to DB
      │
      ▼
7. tts.py  ──►  Piper synthesizes audio  ──►  sounddevice plays it
               ──►  vad.py SpeechInterruptMonitor listens in background
               ──►  If you speak mid-sentence → abort playback → re-listen
```

---

## Technology Stack

| Component | Library | Runs On |
|-----------|---------|---------|
| LLM | `ollama` → `qwen2.5:3b` | **GTX 1660 GPU (CUDA)** |
| Screen Vision | `ollama` → `moondream` | **GTX 1660 GPU (CUDA)** |
| Speech-to-Text | `faster-whisper` (base.en, int8) | **CPU** |
| Text-to-Speech | `piper` (neural) / `pyttsx3` (fallback) | **CPU** |
| Voice Activity Detection | `sounddevice` + `numpy` RMS | CPU |
| Wake Word | `openWakeWord` (hey_jarvis ONNX) | CPU |
| Persistent Memory | `sqlite3` (`jarvis_memory.db`) | Disk |
| Web Search | `playwright` (Chromium) | — |
| App Install | `winget` (Windows Package Manager) | — |
| Screen OCR | Windows WinRT OCR via PowerShell | — |
| Noise Reduction | `noisereduce` | CPU |

---

---

## File: `main.py` — The Orchestrator

**Location:** `jarvis_project/main.py`  
**Size:** 196 lines  
**Role:** The entry point. Controls everything from startup to shutdown.

---

### What it does

`main.py` is the "brain stem" — it doesn't do any AI or audio processing itself, but it wires every other module together and drives the main conversation loop. Think of it as the director that tells everyone else when to act.

---

### Startup Sequence

When you run `python main.py`, this happens in order:

1. **Load memory** from the SQLite database so JARVIS remembers your previous conversations.
2. **Print audio device info** so you can diagnose microphone problems.
3. **Start the background system monitor** on a daemon thread.
4. **Ask you to pick an input mode** (1/2/3/4).
5. **Load the wake word detector** if modes 1 or 3 are selected.
6. **Greet you** with a time-aware greeting ("Good morning/afternoon/evening, sir").
7. **Enter the main `while True` loop.**

---

### Input Modes

You pick one of four modes at startup:

| Mode | Name | How it triggers |
|------|------|-----------------|
| `1` | Wake Word Only | Say "Hey Jarvis" |
| `2` | Push-to-Talk | Hold `CTRL` key |
| `3` | Combined (default) | Either "Hey Jarvis" OR `CTRL` |
| `4` | Always Listening | Classic VAD, always recording |

---

### The Main Loop (lines 125–191)

The heart of the program. Every iteration:

```python
while True:
    # 1. Wait for trigger (wake word / key / VAD)
    user_text = stt.listen_and_transcribe()

    # 2. Check exit commands ("quit", "exit", "stop", "goodbye")
    if user_text in EXIT_COMMANDS:
        tts.speak("Goodbye, sir.")
        return

    # 3. Check memory-wipe commands ("forget everything", "clear memory", ...)
    if user_text in FORGET_COMMANDS:
        memory.clear_history()
        ...

    # 4. Save user message to DB
    memory.append_message('user', user_text)

    # 5. Ask the LLM
    response = llm.query_jarvis(user_text, history)

    # 6. Save JARVIS response to DB
    memory.append_message('assistant', response)

    # 7. Speak — if interrupted, immediately re-listen
    if tts.speak(response):   # returns True if user interrupted
        user_text = stt.listen_and_transcribe(max_wait=8.0)
        continue  # go back into the inner while loop
```

The **inner `while user_text` loop** handles the case where you interrupt JARVIS — it lets you chain responses without going back to the wake word / PTT trigger.

---

### Background System Monitor (`_monitor_system`)

Runs silently on a **daemon thread** in parallel with the conversation. Every 60 seconds it checks:

| Check | Threshold | Action |
|-------|-----------|--------|
| Disk C: free space | < 5 GB | Announces "storage critically low" |
| CPU usage | > 90% | Announces "CPU critically high" |
| RAM usage | > 90% | Announces "memory critically high" |

Uses `shutil.disk_usage()` and `psutil` — no external tools needed.

---

### Helper Functions

| Function | Purpose |
|----------|---------|
| `_print_audio_info()` | Shows microphone name and sample rate at startup |
| `_greeting()` | Returns "Good morning/afternoon/evening" based on current hour |
| `_normalize(text)` | Strips punctuation and lowercases for command matching |

---

### Key Design Decisions

- **`EXIT_COMMANDS`** and **`FORGET_COMMANDS`** are plain `set` lookups — O(1), no regex needed.
- The monitor thread is `daemon=True` — it dies automatically when the main loop exits.
- History is maintained **both** in-memory (the `history` list) for the LLM and in SQLite (for restarts). They stay in sync after every turn.

---

---

## File: `llm.py` — The LLM Brain

**Location:** `jarvis_project/llm.py`  
**Size:** 470 lines  
**Role:** All Ollama interaction, JARVIS's personality, tool definitions, and the tool-calling loop.

---

### What it does

`llm.py` is the actual intelligence layer. It:
- Gives JARVIS its personality and live context awareness.
- Defines 18 tools the model can call.
- Runs a multi-turn tool loop until the model produces a plain text answer.
- Routes every tool call to the right Python function.

---

### The System Prompt (`_build_system_prompt`)

Built fresh on **every single query** so time/date is always accurate. Contains:

**1. Persona definition**
> "You are JARVIS, Tony Stark's personal AI assistant from Iron Man, running locally on this machine. You are sharp, efficient, and composed, with a dry and courteous wit."

**2. Agentic rules** — what ALWAYS triggers a tool call:
- User asks to open/launch/start anything → `open_app`
- User asks about disk/storage → `check_disk_space`
- User asks to install anything → `install_app`
- User mentions something personal → `remember_fact`
- User asks what you know about them → `recall_facts`

**3. Speech style rules**
- Speak naturally, use contractions.
- Short sentences. Vary rhythm. No robotic lists.
- Brief acknowledgment when acting: *"Checking storage... 42 GB free. Installing now, sir."*

**4. Self-upgrade awareness**
- JARVIS knows it can read and modify its own source files.
- Instructed to never remove safety systems, never break imports.

**5. Live injected context** (re-evaluated each call)
```python
f"Date/time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}"
f"Period of day: {period}"
f"Host machine: {platform.node()}"
f"OS: {platform.system()} {platform.release()}"
```

---

### The 18 Tools

Defined in `available_tools` as a list of JSON Schema objects that Ollama reads to know what it can call:

| Tool | Category | What it does |
|------|----------|--------------|
| `open_app` | App Control | Launch Windows apps or open websites |
| `install_app` | App Control | Download & install via winget |
| `get_system_stats` | System Info | CPU, RAM, GPU percentages |
| `run_cmd` | System Info | Run safe read-only PowerShell commands |
| `check_disk_space` | System Info | Disk total/used/free for a drive |
| `jarvis_search` | Web | Google search via Playwright |
| `describe_screen` | Vision | OCR all text on screen |
| `capture_and_analyze_screen` | Vision | Moondream vision model answers questions about screen |
| `list_project_files` | Self-Inspection | Lists JARVIS's own source files |
| `read_project_file` | Self-Inspection | Reads contents of a source file |
| `apply_code_change` | Self-Modification | Safely rewrites a source file with backup + syntax check |
| `restore_backup` | Self-Modification | Restores the last backup of a source file |
| `remember_fact` | Memory | Saves a fact about the user to SQLite |
| `recall_facts` | Memory | Searches saved facts |
| `forget_fact` | Memory | Deletes a saved fact by ID |
| `write_sandbox_file` | Sandbox | Writes a file into the isolated sandbox directory |
| `read_sandbox_file` | Sandbox | Reads a file from the sandbox |
| `run_sandbox_code` | Sandbox | Executes a Python script in the sandbox |

---

### The Tool Loop (`query_jarvis`)

This is the core engine. It runs a maximum of **5 tool-call rounds**:

```
messages = [system_prompt] + history[-20] + [user_message]

for _ in range(5):
    response = ollama.chat(model='qwen2.5:3b', messages=messages, tools=available_tools)

    if response has NO tool_calls:
        return response.message.content   ← Done!

    # Execute each requested tool
    for tool_call in response.message.tool_calls:
        result = _dispatch_tool(tool_call.function.name, tool_call.function.arguments)
        messages.append({'role': 'tool', 'content': result})

# If 5 rounds exhausted without a plain answer:
response = ollama.chat(model='qwen2.5:3b', messages=messages)
return response.message.content
```

This means for a single user request like *"Install Spotify"*, JARVIS can:
1. Call `check_disk_space` → reads 142 GB free.
2. Call `install_app("Spotify")` → launches the installer.
3. Return a verbal confirmation — **all in one response**.

---

### Tool Dispatcher (`_dispatch_tool`)

A big `if/elif` chain that maps tool names to Python calls with safe type-casting:

```python
if name == 'open_app':
    return tools.open_app(str(args.get('app_name', '')))
if name == 'forget_fact':
    return tools.forget_fact(int(args.get('fact_id', 0)))  # forced int cast
...
```

Unknown tool names return `"Unknown tool: {name}"` — they never raise exceptions.

---

---

## File: `tools.py` — OS Actions & Capabilities

**Location:** `jarvis_project/tools.py`  
**Size:** 782 lines  
**Role:** Every real-world action JARVIS can perform. The largest file.

---

### What it does

`tools.py` implements the actual capability functions. Every function the LLM can call lives here (except sandbox functions). Strong focus on **security** — no function blindly trusts its input.

---

### `find_app_path(executable_name)` — App Discovery

Used internally by `open_app`. Searches for an `.exe` in three places:

1. **System PATH** via `shutil.which()`
2. **Windows Registry** — checks `HKCU` and `HKLM` under `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe}` — this is how properly installed apps register themselves.
3. **Standard install directories** — `Program Files`, `Program Files (x86)`, `AppData\Local` — with hardcoded known subpaths for Brave, Chrome, and Edge.

Returns the full absolute path or `None` if not found.

---

### `open_app(app_name)` — Launch Apps & Websites

**Two code paths:**

**Website path** (if input is a URL or mapped name like "youtube"):
- Maps friendly names → URLs: `youtube` → `https://www.youtube.com`, etc.
- Validates URL with regex `^https?://[^\s"']+$` to block injection.
- Checks if a browser is already running via `get_running_browser_exe()` → opens in it.
- Falls back to `webbrowser.open()` if no browser is running.
- All `subprocess.Popen()` calls use **list args** (not `shell=True`) to prevent command injection even if the URL is malicious.

**App path** (if input is an app name):
- Maps friendly names → executables: `"brave"` → `brave.exe`, `"breathe"` → `brave.exe` (handles STT mishearing of "Brave"!), `"calculator"` → `calc.exe`, etc.
- For non-system apps, calls `find_app_path()` to resolve the real path.
- Validates the executable name with regex `^[\w.\- ]+\.exe$`.
- Launches with `subprocess.Popen([resolved_path])` — no shell, no injection.

---

### `get_system_stats()` — System Performance

Returns CPU%, RAM%, and GPU%:
- CPU: `psutil.cpu_percent(interval=0.1)`
- RAM: `psutil.virtual_memory().percent`
- GPU: Runs `nvidia-smi --query-gpu=utilization.gpu,utilization.memory --format=csv,noheader,nounits` if `nvidia-smi` is on PATH. Falls back to "Not available" gracefully.

---

### `run_cmd(command)` — Sandboxed PowerShell

**The most locked-down function in the codebase.** Two security layers:

**Layer 1 — Block denylist:**
Any command containing these tokens is refused before execution:
```
remove-item, rm, del, erase, format, shutdown, restart-computer,
stop-computer, taskkill, kill, stop-process, reg delete, reg add,
net user, net localgroup, wmic, schtasks, bcdedit, diskpart,
invoke-expression, iex, >, >>, |, ;, &&, ||
```

**Layer 2 — Allowlist prefix check:**
The command must START with one of these safe prefixes:
```
get-, select-, where-, ipconfig, systeminfo, netstat, whoami,
ping, dir, ls, echo, hostname, tasklist, ver, cls, pwd,
get-date, get-process, get-service, get-childitem, ...
```

Both must pass. Then runs via:
```python
subprocess.run(
    ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
    capture_output=True, text=True, timeout=15
)
```

---

### `jarvis_search(query)` — Google Search

Uses **Playwright** (real Chromium browser, not headless so you can watch):
1. Launches Chromium.
2. Navigates to `https://www.google.com`.
3. Fills the `textarea[name='q']` search box.
4. Presses Enter and waits for `h3` elements to appear.
5. Scrapes the first 5 H3 titles.
6. Returns them as a bullet list string.

The model then reads these titles and gives you a verbal summary.

---

### `check_disk_space(drive)` — Disk Space

Simple `shutil.disk_usage()` wrapper. Normalizes the drive string (handles `"C"`, `"C:"`, `"c:\\"`) and returns total/used/free in GB.

---

### `install_app(app_name, force=False)` — App Installation

**Pre-flight checks:**
1. Validates `app_name` with regex (no special chars).
2. Calls `shutil.disk_usage("C:\\")` — if free space < 5 GB and `force=False`, refuses and tells the LLM to warn the user.
3. Checks `shutil.which("winget")` — refuses if winget isn't installed.

**Installation:**
1. Runs `winget search "{app_name}"` to find the exact package ID.
2. Parses the search output to extract the ID (second column of search results).
3. Launches `winget install --id {app_id}` in a **new visible CMD window** using `start cmd /c "..."` — this means JARVIS doesn't block waiting for the install to finish, and you can see the progress.

---

### `describe_screen()` — Screen OCR

1. Captures the full screen with `PIL.ImageGrab.grab()`.
2. Saves to `screenshot.png`.
3. Gets active window title via `win32gui.GetForegroundWindow()`.
4. Runs **Windows' native WinRT OCR engine** via a PowerShell script that loads `Windows.Media.Ocr.OcrEngine` — this is the same engine Windows uses for its built-in OCR, works offline.
5. Returns the window title + all detected text.
6. Cleans up `screenshot.png` in a `finally` block.

---

### `capture_and_analyze_screen(prompt)` — Vision AI

Uses `mss` (faster than Pillow for screenshots):
1. Grabs the full monitor as a PNG in memory.
2. Base64-encodes it.
3. Normalizes generic questions like "what's on my screen?" → "Describe this screen in detail." (Moondream handles specific phrasing poorly).
4. Sends to **Moondream vision model** via `ollama.chat()` with the image.
5. If Moondream returns nothing, retries with the generic description prompt.
6. Prepends the active window title for extra context.

---

### Self-Modification Tools

These three form JARVIS's self-upgrade capability:

#### `list_project_files()`
Lists `.py` and `.md` files in `PROJECT_DIR`, skipping blocked directories (`.venv`, `voices`, `__pycache__`, `.git`, `.jarvis_backups`).

#### `read_project_file(filename)`
- Blocks path traversal via `_safe_project_path()` — verifies the resolved path is inside `PROJECT_DIR`.
- Refuses blocked dirs.
- Only allows `.py`, `.md`, `.txt`, `.json` extensions.
- Truncates at 12,000 characters to avoid flooding the LLM context.

#### `apply_code_change(filename, new_code)`
The most critical self-modification function. Steps:
1. Validates filename is a `.py` file in the project dir, not blocked.
2. Reads original file into memory.
3. Creates backup: `{timestamp}_{filename}` in `.jarvis_backups/`.
4. Writes new code to the file.
5. Runs `py_compile.compile(full, doraise=True)` — catches ANY syntax error.
6. If compile fails → restores original from memory immediately.
7. Returns success message with backup filename so JARVIS can confirm.
8. **Changes only take effect after restart** (Python modules don't hot-reload).

#### `restore_backup(filename)`
Finds all backups matching `*_{filename}` in `.jarvis_backups/`, sorts them alphabetically (timestamps sort correctly), and copies the last one back.

---

### Memory Delegators

These three functions just call `memory.py` and format the output nicely:

- `remember_fact(fact)` → `memory.add_fact(fact)` → returns ID confirmation.
- `recall_facts(query)` → `memory.get_facts(query)` → formats as a readable list with IDs.
- `forget_fact(fact_id)` → `memory.delete_fact(fact_id)` → confirms deletion.

---

---

## File: `stt.py` — Speech-to-Text

**Location:** `jarvis_project/stt.py`  
**Size:** 159 lines  
**Role:** Microphone capture and Whisper transcription. Forced to CPU.

---

### What it does

Captures audio from the microphone (in one of two modes), preprocesses it, and feeds it to `faster-whisper` for transcription. The model is kept on **CPU** to preserve VRAM for Ollama.

---

### Model Loading — Lazy + Cached

```python
_model = None

def get_whisper_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel("base.en", device="cpu", compute_type="int8")
    return _model
```

The model loads once (takes ~2 seconds the first time) and stays in RAM for the entire session. Every subsequent transcription is instant. Using `int8` quantization halves memory usage at minimal accuracy cost for English speech.

---

### Audio Preprocessing Pipeline

Before sending audio to Whisper, two preprocessing steps run:

#### Step 1: `_normalize(audio)`
Many microphones record quietly. This function:
- Converts to float32.
- Finds the peak amplitude.
- Applies gain so the peak reaches 90% of maximum (`target_peak=0.9`).
- **Caps gain at 5×** to avoid amplifying pure noise to a useless signal.
- Clips to int16 range to prevent distortion.

#### Step 2: `_reduce_noise(audio, sample_rate)` (if `USE_NOISE_REDUCTION=True`)
Removes stationary background noise (fan hum, AC, etc.):
- Takes the first 0.25 seconds as the "noise profile" — assumes that's silence.
- Checks if that segment is actually quiet (RMS < 60). If speech starts immediately, skips to avoid mangling it.
- Runs `noisereduce.reduce_noise()` with `stationary=True`.
- Result clipped back to int16.

Set `USE_NOISE_REDUCTION = False` in the file if it feels too slow on your machine.

---

### `transcribe_audio(audio, sample_rate)`

The main transcription function:
1. Runs `_normalize` then `_reduce_noise`.
2. Writes to `temp.wav` using `scipy.io.wavfile.write()`.
3. Runs `model.transcribe(TEMP_WAV, beam_size=5)` — beam search width 5 balances accuracy vs. speed.
4. Joins all segments into a single string.
5. Deletes `temp.wav` in a `finally` block regardless of outcome.

---

### Recording Mode 1: `listen_and_transcribe(max_wait=8.0)`

Standard VAD-based recording. Delegates to `UtteranceRecorder` in `vad.py`:
- Waits silently for you to start speaking (up to `max_wait` seconds).
- Records until you pause for ~0.7 seconds.
- Returns the audio to `transcribe_audio()`.

Used by: Wake Word mode, Always Listening mode, post-interrupt re-listen.

---

### Recording Mode 2: `listen_and_transcribe_ptt(key="ctrl")`

Push-to-Talk recording:
1. Polls `keyboard.is_pressed(key)` in a 50ms loop until the key is down.
2. Opens a `sounddevice.InputStream` callback that collects `audio_chunks`.
3. Keeps the stream open while the key is held.
4. On key release: concatenates all chunks and passes to `transcribe_audio()`.

Used by: Push-to-Talk mode and the Combined mode when CTRL is pressed.

---

---

## File: `tts.py` — Text-to-Speech

**Location:** `jarvis_project/tts.py`  
**Size:** 138 lines  
**Role:** Converts JARVIS's text responses into spoken audio with real-time barge-in support.

---

### What it does

Speaks text aloud using either a neural Piper voice (if available) or `pyttsx3` as a fallback. The key feature: detects if you start talking while JARVIS speaks and stops **instantly**, so your voice isn't drowned out or echoed back into the microphone.

---

### Voice Priority

```
1. Piper (en_GB-alan-medium.onnx) ← preferred: neural, sounds natural
        ↓ (file missing or import fails)
2. pyttsx3 (Windows SAPI)         ← fallback: robotic but reliable
```

The Piper model file (`voices/en_GB-alan-medium.onnx`) must be downloaded separately. Both voice objects are **lazily initialized and cached** — they load once, not on every call.

---

### `_synth_piper_audio(text)`

Synthesizes audio with Piper **entirely in memory** (no temp files):
1. Creates an in-memory `io.BytesIO()` buffer.
2. Opens it as a WAV file object.
3. Calls `voice.synthesize_wav(text, wav_file)`.
4. Seeks back to the start and reads with `scipy.io.wavfile.read()`.
5. Converts to mono int16 numpy array.

Returns `(sample_rate, audio_array)` ready for `sounddevice`.

---

### `_speak_piper_bargeable(text)` — The Key Function

This is what makes JARVIS feel responsive instead of robotic:

```
1. Arm SpeechInterruptMonitor (opens microphone listener)
2. Synthesize full audio with Piper → numpy array
3. Split into 2048-sample chunks (~93ms each)
4. For each chunk:
   a. Check monitor.was_interrupted() → if True: abort()
   b. Write chunk to sounddevice OutputStream
5. After last chunk: wait 100ms grace window for late interruption
6. Return True if interrupted, False if finished normally
```

`out.abort()` is critical — it **discards all buffered audio immediately** rather than playing it out. Without this, there'd be a half-second of JARVIS's voice still playing after you interrupted.

If the microphone can't be opened (mic unavailable), falls back to blocking `sd.play()` with no barge-in support.

---

### `speak(text)` — Public Interface

The only function `main.py` ever calls:
- Strips the text.
- If Piper is available AND the `.onnx` model file exists → `_speak_piper_bargeable()`.
- Otherwise → `_speak_pyttsx3()`.
- Returns `True` if the user interrupted, `False` if playback finished.

`main.py` checks the return value to decide whether to immediately re-listen.

---

---

## File: `vad.py` — Voice Activity Detection

**Location:** `jarvis_project/vad.py`  
**Size:** 167 lines  
**Role:** Low-level audio primitives used by both `stt.py` and `tts.py`. Nothing else imports this directly.

---

### What it does

Two classes that handle the hard parts of working with live audio:
1. Detecting when you start speaking while JARVIS is talking (barge-in).
2. Recording a complete utterance from start to end (VAD-based capture).

### Constants

```python
SAMPLE_RATE = 16000       # Hz — Whisper's native sample rate
BLOCK_SIZE = 1024         # samples per audio chunk (~64ms)
RMS_THRESHOLD = 500       # int16 amplitude — tune if you have mic echo
MIN_SPEECH_BLOCKS = 3     # 3 consecutive loud blocks = ~192ms of real speech
MAX_BUFFER_BLOCKS = ...   # ~12 seconds of rolling buffer
```

`RMS_THRESHOLD = 500` means the audio's root-mean-square amplitude must be above 500/32767 ≈ 1.5% of max. This filters out background hiss and quiet room noise.

---

### Class: `SpeechInterruptMonitor`

Used exclusively by `tts.py`. Monitors the microphone **in the background while JARVIS speaks**.

**How it detects a real interruption (not noise):**

```python
if rms > RMS_THRESHOLD:
    self._speech_blocks += 1       # count consecutive loud blocks
    if self._speech_blocks >= MIN_SPEECH_BLOCKS:   # 3 blocks = ~192ms
        self._triggered = True
        self._interrupt.set()       # signal tts.py to stop
else:
    self._speech_blocks = 0         # reset counter on any quiet block
```

Requires **3 consecutive** loud blocks before triggering. A single loud block (like a click or brief noise) resets the counter. This prevents audio glitches from causing false interrupts.

**API used by `tts.py`:**
- `arm()` — opens microphone stream, returns `True` if successful.
- `was_interrupted()` — checked after every audio chunk during playback.
- `wait(timeout)` — blocks for a short grace window at the end of playback.
- `close()` — stops and closes the microphone stream.

---

### Class: `UtteranceRecorder`

Used exclusively by `stt.py`. Records one complete spoken utterance from start to finish.

**State machine:**

```
"waiting" state:
    - Keeps a rolling ring buffer of the last 0.5s (pre-roll)
    - Counts consecutive loud blocks
    - When MIN_SPEECH_BLOCKS consecutive loud → switch to "recording"
    - Include the pre-roll in the recording (captures speech onset)
    - Give up after max_wait seconds with no speech

"recording" state:
    - Appends every audio block
    - Resets silence counter when loud, increments when quiet
    - When min_silence_blocks (0.7s) of quiet → stop
    - Hard cap at max_utterance = 15 seconds
```

The **pre-roll** is a clever detail — because VAD can only detect speech after it starts, the first few milliseconds would otherwise be clipped. By including the last 0.5s of audio from the "waiting" phase, the beginning of your sentence is always captured.

---

---

## File: `wakeword.py` — Wake Word Detection

**Location:** `jarvis_project/wakeword.py`  
**Size:** 80 lines  
**Role:** Listens continuously for "Hey Jarvis" using a pre-trained ONNX model.

---

### What it does

Uses **openWakeWord** — an open-source library with pre-trained models for common wake phrases — to detect "Hey Jarvis" without sending audio anywhere.

---

### `WakeWordDetector` Class

**Initialization:**
```python
self.oww_model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
```
Loads the `hey_jarvis.onnx` model at startup. ONNX runtime means it runs fast on CPU.

**Audio format requirements:**
- 16kHz sample rate
- Mono (1 channel)
- 16-bit PCM integer
- Chunks of exactly **1280 samples** (80ms) — the format openWakeWord expects.

---

### `listen_for_wake_word()`

Blocking loop:
```python
while True:
    data, overflowed = stream.read(CHUNK_SIZE)
    if overflowed:
        continue  # skip corrupted chunks
    chunk = data[:, 0]   # take mono channel
    prediction = self.oww_model.predict(chunk)
    prob = prediction.get("hey_jarvis", 0.0)
    if prob >= 0.5:      # threshold = 50% confidence
        return True
```

Prints the confidence score when detected: `[WAKE WORD] Detected 'hey_jarvis' with confidence 0.87!`

---

### `listen_for_wake_word_or_ptt(ptt_key="ctrl")`

Same loop but also checks the keyboard:
```python
while True:
    if keyboard.is_pressed(ptt_key):
        return "ptt"       # PTT key pressed first
    # ... check wake word ...
    if prob >= 0.5:
        return "wakeword"  # wake word heard first
```

Returns a string so `main.py` knows which trigger fired and handles them differently (PTT starts recording immediately; wake word first records a fresh VAD utterance).

---

---

## File: `memory.py` — Persistent Memory

**Location:** `jarvis_project/memory.py`  
**Size:** 131 lines  
**Role:** All SQLite database operations for conversation history and long-term facts.

---

### What it does

Manages two persistent memory systems:
1. **Conversation history** — the last N turns of dialogue, so JARVIS remembers what you said earlier in the session AND across restarts.
2. **Fact memory** — explicitly saved facts about you ("User's name is Abhishek", "User prefers dark mode"), searchable and deletable.

---

### Database Schema

**`history` table** — conversation messages:
```sql
CREATE TABLE IF NOT EXISTS history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    role      TEXT NOT NULL,      -- "user" or "assistant"
    content   TEXT NOT NULL,      -- the message text
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

**`facts` table** — long-term memory:
```sql
CREATE TABLE IF NOT EXISTS facts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    fact      TEXT NOT NULL,      -- e.g. "User's favorite language is Python"
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

Database file: `jarvis_project/jarvis_memory.db` (created automatically).

---

### History Functions

| Function | SQL | Notes |
|----------|-----|-------|
| `load_history()` | `SELECT role, content FROM history ORDER BY id DESC LIMIT 40` | Fetches 40 rows (20 turns), reverses to chronological order |
| `append_message(role, content)` | `INSERT INTO history ...` | Called after EVERY message — real-time persistence |
| `clear_history()` | `DELETE FROM history` | Triggered by "forget everything" voice command |

`MAX_TURNS = 20` → loads 40 messages (user + assistant per turn). The LLM sees at most 20 turns of history, keeping context size manageable.

---

### Fact Functions

| Function | SQL | Notes |
|----------|-----|-------|
| `add_fact(fact)` | `INSERT INTO facts (fact) VALUES (?)` | Returns `lastrowid` (the ID) |
| `get_facts(query)` | `SELECT ... WHERE fact LIKE ?` or all if no query | LIKE uses `%query%` for fuzzy match |
| `delete_fact(fact_id)` | `DELETE FROM facts WHERE id = ?` | Returns `cursor.rowcount > 0` to confirm deletion |

---

### Safety Design

- `init_db()` is called at the **top level on import** — database and tables are created automatically the first time `memory.py` is imported.
- `init_db()` is also called **defensively** at the start of every function — handles the case where the DB file was deleted externally.
- All SQL uses **parameterized queries** (`?` placeholders) — immune to SQL injection.
- All `sqlite3.Error` exceptions are caught silently — the app keeps running even if the DB has issues.

---

---

## File: `sandbox_tools.py` — Safe Code Execution

**Location:** `jarvis_project/sandbox_tools.py`  
**Size:** 78 lines  
**Role:** Isolated file system and Python execution environment for JARVIS's coding tools.

---

### What it does

Provides a strictly isolated `sandbox/` directory where JARVIS can write, read, and run Python code without any risk of touching the project files or the system.

---

### Security: Path Sanitization

```python
def _sanitize_path(filename: str) -> str:
    base_name = os.path.basename(filename)          # strip ALL directory components
    target_path = os.path.abspath(os.path.join(SANDBOX_DIR, base_name))
    if not target_path.startswith(os.path.abspath(SANDBOX_DIR)):
        raise ValueError("Access denied: ...")
    return target_path
```

`os.path.basename()` strips everything — so `"../../main.py"` becomes `"main.py"` and lands in the sandbox, not the project root. The `startswith` check is a final safety net against any edge cases.

---

### `write_sandbox_file(filename, content)`

1. Calls `_sanitize_path()`.
2. Opens the file in the sandbox directory and writes content.
3. Returns a success string.

Simple. The security is entirely in `_sanitize_path`.

---

### `read_sandbox_file(filename)`

1. Sanitizes path.
2. Checks the file exists.
3. Reads and returns content as a string.

---

### `run_sandbox_code(filename)`

Executes a Python script in the sandbox:

```python
venv_python = ".venv/Scripts/python.exe"  # use project's venv if it exists
python_exe = venv_python if os.path.exists(venv_python) else sys.executable

result = subprocess.run(
    [python_exe, path],
    capture_output=True,
    text=True,
    cwd=SANDBOX_DIR,     # working directory is the sandbox
    timeout=15            # hard 15-second timeout
)
```

Returns a dict:
```python
{
    "success": result.returncode == 0,
    "returncode": result.returncode,
    "stdout": result.stdout,
    "stderr": result.stderr
}
```

Return codes:
- `-1` → file not found
- `-2` → timed out (15s limit exceeded)
- `-3` → unexpected execution error
- `0` → success
- Non-zero → script itself exited with an error

---

---

## File: `self_evolve.py` — Autonomous Code Generation

**Location:** `jarvis_project/self_evolve.py`  
**Size:** 75 lines  
**Role:** Generate → Test → Auto-debug Python code in a loop using the LLM.

---

### What it does

An independent agentic reasoning loop. Given a plain-English coding task, it:
1. Asks the LLM to write Python code.
2. Runs it in the sandbox.
3. If it crashes, feeds the error back to the LLM and asks for a fix.
4. Repeats up to `max_retries` times.

This is the same "generate → evaluate → fix" pattern used by modern coding agents, implemented in ~75 lines.

---

### `evolve_code(prompt, filename, max_retries=5)`

**System prompt used:**
> "You are an expert Python developer. Generate raw Python code to solve the user's task. Your response MUST contain ONLY the Python code inside a markdown code block (```python ... ```) and nothing else."

**The loop:**

```
messages = [system_prompt, user_prompt]

for attempt in 1..max_retries:
    response = ollama.chat(qwen2.5:3b, messages)
    
    # Extract code from ```python ... ``` block
    code = extract_from_markdown(response)
    
    # Write to sandbox and run it
    write_sandbox_file(filename, code)
    result = run_sandbox_code(filename)
    
    if result["success"]:
        return {success: True, code, stdout}
    
    # Feed error back to the model
    messages.append({"role": "assistant", "content": response})
    messages.append({"role": "user", "content": f"Code failed:\n{stderr}\nFix it."})

return {success: False, error: stderr}
```

**Code extraction** handles three formats:
1. ` ```python ... ``` ` — preferred
2. ` ``` ... ``` ` — plain block
3. Raw output — used as-is

The model receives its own previous attempt in the message history — it can see what it tried and why it failed, which gives it context to produce a better fix.

---

---

## File: `demo_self_evolve.py` — Demo Runner

**Location:** `jarvis_project/demo_self_evolve.py`  
**Size:** 41 lines  
**Role:** Standalone demo showing the self-evolution pipeline with a deliberately broken first attempt.

---

### What it does

A small script that demonstrates the full self-evolution loop end-to-end. It's not part of the main JARVIS runtime — you run it separately.

---

### The Task (Deliberately Broken)

```python
task = (
    "Write a Python script that calculates the average of a list of numbers. "
    "IMPORTANT: In your first attempt, do NOT check if the list is empty. "
    "Simply divide the sum by the length of the list, and execute this function "
    "passing an empty list []. This will cause a ZeroDivisionError to test our "
    "auto-debugging/evaluator pipeline."
)
```

The model is **instructed to write buggy code on the first attempt**. This guarantees the error loop triggers, so you can watch the full generate → fail → fix cycle in action.

---

### Expected Output

```
Attempt 1: Writes code without empty-list check → ZeroDivisionError
[STDERR]: ZeroDivisionError: division by zero

Attempt 2: Model sees its own error → fixes it → adds `if len(numbers) == 0: return 0`
[STDOUT]: The average is: 0  (or handles gracefully)

Success on attempt 2!
```

---

### Running It

```bash
cd jarvis_project
python demo_self_evolve.py
```

You'll see live output from the `[EVOLVE]` prefix log lines as each attempt runs.

---

---

## Summary Table

| File | Lines | Depends On | Used By |
|------|-------|------------|---------|
| `main.py` | 196 | `stt`, `llm`, `tts`, `memory`, `wakeword` | — (entry point) |
| `llm.py` | 470 | `ollama`, `tools`, `sandbox_tools` | `main.py` |
| `tools.py` | 782 | `psutil`, `playwright`, `ollama`, `memory` | `llm.py` |
| `stt.py` | 159 | `faster_whisper`, `vad`, `noisereduce` | `main.py` |
| `tts.py` | 138 | `piper`, `pyttsx3`, `vad`, `sounddevice` | `main.py` |
| `vad.py` | 167 | `sounddevice`, `numpy` | `stt.py`, `tts.py` |
| `wakeword.py` | 80 | `openwakeword`, `sounddevice` | `main.py` |
| `memory.py` | 131 | `sqlite3` | `main.py`, `tools.py` |
| `sandbox_tools.py` | 78 | `subprocess`, `os` | `llm.py`, `self_evolve.py` |
| `self_evolve.py` | 75 | `ollama`, `sandbox_tools` | `demo_self_evolve.py` |
| `demo_self_evolve.py` | 41 | `self_evolve`, `sandbox_tools` | — (standalone demo) |

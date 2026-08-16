# JARVIS Execution Guide

This guide explains how to run **JARVIS (Fully Local Voice & Text AI Assistant)**.

---

## 1. Quick Start (1-Click Launcher)

The easiest way to start Jarvis from PowerShell:

### Voice Mode (Microphone + Speaker)
```powershell
.\run_jarvis.ps1
```
- Say **"Hey Jarvis"** to wake him up!
- Ask questions, control your system, play YouTube videos, check storage, etc.
- **Barge-In**: You can interrupt Jarvis while he is speaking.

### Text / Chat Mode (Keyboard only)
```powershell
.\run_jarvis.ps1 -Text
```
- Lets you chat with the 3-tier LLM router, memory, and tools without needing a microphone.

---

## 2. Architecture & Smoke Testing

To verify model residency, CPU/GPU hardware split, and tools:
```powershell
.\jarvis_project\.venv\Scripts\python.exe tier_smoke_test.py
```

---

## 3. Manual Virtual Environment Setup (Optional)

If running commands manually without `run_jarvis.ps1`:
```powershell
cd jarvis_project
.\.venv\Scripts\Activate.ps1
python main.py
```

---

## 4. Key Capabilities
- **Voice Pipeline**: openWakeWord (`Hey Jarvis`) + Silero VAD + faster-whisper (CPU int8) + Piper neural TTS.
- **3-Tier AI Router**: Flash Tier (`qwen2.5:3b` in 4GB GPU VRAM) + Pro Coder Tier (`qwen3-coder:30b` in CPU RAM) + Vision Tier (`gemma4:e4b`).
- **Tools**: Real YouTube playback (`play_youtube`), safe URL navigation (`open_url`), system diagnosis, RAG second brain (`rag.py`), autonomous background pulse (`pulse.py`), and smart home controls.

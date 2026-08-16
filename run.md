# JARVIS & 4-Agent Swarm Execution Guide

This guide explains how to run **Jarvis (Local Voice Assistant)** and the **4-Agent Multi-Agent Swarm (`agy`, `opencode`, `cline`, `kilo`)**.

---

## Part 1: How to Run JARVIS (AI Voice Assistant)

### Prerequisites:
Make sure your Python virtual environment is ready:
```powershell
# Activate project virtual environment
.\jarvis_project\.venv\Scripts\Activate.ps1
```

### 1. Run Jarvis in Voice Mode (Microphone + Speaker)
Starts the real-time audio loop, listening for the wake word *"Hey Jarvis"*:
```powershell
cd jarvis_project
python main.py
```
- **Wake Word**: Say *"Hey Jarvis"*.
- **Speak**: Ask your question or command (e.g. *"What's the weather?"*, *"Check my disk space"*).
- **Barge-In**: You can interrupt Jarvis while it speaks.

### 2. Run Jarvis in Text / Chat Mode (No Audio)
Test the 3-tier LLM router, memory, and tools from your keyboard without using microphone/TTS:
```powershell
cd jarvis_project
python main.py --text
```

### 3. Run Architecture Smoke Tests
Verifies model residency, CPU/GPU tier splits, and tool execution:
```powershell
.\jarvis_project\.venv\Scripts\python.exe tier_smoke_test.py
```

---

## Part 2: How to Run the 4-Agent Autonomous Swarm

The Swarm lets 4 AI coding agents work in parallel on your codebase across isolated Git worktrees without file conflicts.

```
┌─────────────────────────────────┬─────────────────────────────────┐
│ PANE 1: Lead Director (agy)     │ PANE 2: Backend (opencode)      │
│ Folder: M:\coding\Jarvis        │ Folder: M:\coding\Jarvis-backend│
├─────────────────────────────────┼─────────────────────────────────┤
│ PANE 3: Frontend (cline)        │ PANE 4: QA & Ponytail (kilo)    │
│ Folder: M:\coding\Jarvis-front  │ Folder: M:\coding\Jarvis-qa     │
└─────────────────────────────────┴─────────────────────────────────┘
```

### Step 1: Launch the 4-Pane Grid
From PowerShell in the root directory:
```powershell
.\swarm\start_swarm.ps1
```
*Windows Terminal opens automatically in a 2x2 split grid with all 3 worker daemons watching for tasks.*

---

### Step 2: Give a Goal in Pane 1 (Top-Left)
Click into **Pane 1** and type:
```powershell
python swarm/dispatch.py "Add a real-time audio visualizer to the UI"
```

---

### Step 3: Sit Back and Watch Them Build! ☕
- **Pane 2 (`opencode`)**: Automatically claims the backend task, writes the API/logic in `Jarvis-backend`, and commits to `agent/backend`.
- **Pane 3 (`cline`)**: Automatically claims the frontend task, builds the UI in `Jarvis-frontend`, and commits to `agent/frontend`.
- **Pane 4 (`kilo`)**: Automatically detects when they finish, runs smoke tests, applies **`ponytail-review`** to strip out any code bloat, and merges the branches into `main`!

---

### Helper Commands Cheat Sheet

| Action | Command | Where to Run |
|---|---|---|
| **Dispatch New Goal** | `python swarm/dispatch.py "feature description"` | Pane 1 (Lead) |
| **View Live Task Status** | `python swarm/swarm_helper.py list` | Any Pane |
| **Get Task Details** | `python swarm/swarm_helper.py get --id <ID>` | Any Pane |
| **Clear Finished Tasks** | `python swarm/swarm_helper.py clear --yes` | Pane 1 |
| **Manually Claim Task** | `python ../Jarvis/swarm/swarm_helper.py next --role <role> --claim` | Panes 2 / 3 |

---

## Part 3: Automatic Token Exhaustion Fallback
If `opencode`, `cline`, or `kilo` ever runs out of tokens or crashes mid-task:
- The worker daemon automatically catches the error.
- The partial work is preserved untouched.
- The task is seamlessly handed off to **`agy`** (Google Gemini Pro 1M+ token context) to finish the implementation and commit without stopping the pipeline!

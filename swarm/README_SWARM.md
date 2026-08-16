# 4-Agent Hybrid CLI Swarm Guide

Welcome to the **Jarvis Multi-Agent Swarm**. This environment coordinates 4 CLI agents working concurrently on separate branches without file conflicts, using a shared blackboard task queue and automated Ponytail code simplification reviews.

---

## 1. Quick Start

Run the launcher script from PowerShell:
```powershell
.\swarm\start_swarm.ps1
```

This will:
1. Verify the Git repository and ensure branches `agent/backend`, `agent/frontend`, and `agent/qa` exist.
2. Create 3 isolated Git Worktrees (`../Jarvis-backend`, `../Jarvis-frontend`, `../Jarvis-qa`).
3. Open a **2x2 split grid in Windows Terminal** with each pane dedicated to a specific agent role.

---

## 2. The 4 Agent Roles

```
┌─────────────────────────────────┬─────────────────────────────────┐
│ Pane 1: LEAD ARCHITECT (CWD: .) │ Pane 2: BACKEND (Jarvis-backend)│
│ Breaks goal into tasks          │ Implements APIs, models, logic  │
├─────────────────────────────────┼─────────────────────────────────┤
│ Pane 3: FRONTEND (Jarvis-front) │ Pane 4: QA & PONYTAIL (Jarvis-qa│
│ Builds UI & client interfaces   │ Runs tests, strips bloat, merges│
└─────────────────────────────────┴─────────────────────────────────┘
```

---

## 3. Coordinating with `swarm_helper.py`

Both you and your CLI agents can manage tasks in the shared queue (`swarm/tasks.json`):

### Lead Agent (Pane 1):
```bash
# Add tasks for worker agents
python swarm/swarm_helper.py add --role backend --title "Create STT audio buffer" --desc "Use standard library wave/queue modules"
python swarm/swarm_helper.py add --role frontend --title "Build audio visualizer component" --desc "Connect to audio buffer endpoint"
python swarm/swarm_helper.py add --role qa --title "Verify STT latency and run ponytail-review"
```

### Worker Agents (Panes 2 & 3):
```bash
# Claim next available task
python ../Jarvis/swarm/swarm_helper.py next --role backend --claim

# ... Write minimal code & commit to git ...

# Mark ready for review
python ../Jarvis/swarm/swarm_helper.py set-status --id 1 --status ready_for_review
```

### QA & Ponytail Reviewer (Pane 4):
```bash
# Check tasks waiting for review
python ../Jarvis/swarm/swarm_helper.py list --status ready_for_review

# Inspect and strip bloat with ponytail-review
agy "ponytail-review git diff against main"

# Merge & mark completed
git checkout main
git merge agent/backend --no-ff
python ../Jarvis/swarm/swarm_helper.py set-status --id 1 --status completed
```

---

## 4. Useful Helper Commands

| Action | Command |
|---|---|
| View All Tasks | `python swarm/swarm_helper.py list` |
| View Pending Backend Tasks | `python swarm/swarm_helper.py list --role backend --status pending` |
| Get Details for Task #2 | `python swarm/swarm_helper.py get --id 2` |
| Clear Finished Tasks | `python swarm/swarm_helper.py clear --yes` |

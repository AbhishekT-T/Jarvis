# MULTI_AGENT_PROTOCOL.md — Swarm Execution & Collaboration Rules

> **MANDATORY FOR MULTI-AGENT SWARMS & PARALLEL SESSIONS:**  
> This document specifies how multiple AI agents coordinate simultaneously on the JARVIS codebase without file collision, merge conflicts, or state corruption.

---

## 1. Principles of Multi-Agent Operation

1. **Explicit File Locking via [plan.md](file:///m:/coding/Jarvis/plan.md):** No agent may modify a file unless it has claimed the corresponding task ticket and locked the file in the shared task board.
2. **Git Worktree Isolation:** When two or more agents are writing code simultaneously, each agent MUST work in its own isolated Git worktree or feature branch.
3. **Strict Interface Integrity:** Agents must honor [ARCHITECTURE.md](file:///m:/coding/Jarvis/ARCHITECTURE.md). You may optimize an internal function, but you may NEVER change public function signatures, parameter names, or database column names without an explicit architectural task ticket.
4. **Ponytail Simplicity Rule:** Eliminate bloat. Use standard library and installed dependencies first. One line before fifty. Verify changes before marking complete.

---

## 2. Git Worktree Isolation Protocol

When multiple agents run in parallel (e.g., Backend Agent improving audio while Frontend Agent refines the HUD), working in the same working tree causes Git unstaged file collisions.

### 2.1 Spawning an Isolated Agent Worktree
Agents should operate in dedicated Git worktrees mapped to their specific domain:

```powershell
# 1. Ensure main branch is clean
git fetch origin main

# 2. Spawn isolated worktree for your domain role
# Example for Audio/VoiceOS Agent:
git worktree add -b feat/audio-inmemory-whisper ../Jarvis-audio origin/main

# Example for Frontend/HUD Agent:
git worktree add -b feat/hud-websocket-streaming ../Jarvis-frontend origin/main

# Example for Tool Optimization Agent:
git worktree add -b feat/tools-ddgs-search ../Jarvis-tools origin/main
```

### 2.2 Releasing and Pruning Worktrees
Once the branch is merged into `main`:
```powershell
git worktree remove ../Jarvis-audio
git branch -d feat/audio-inmemory-whisper
```

---

## 3. The Task Claim & File Locking Protocol

Before touching ANY file, an agent must consult the **Active Task Board** in [plan.md](file:///m:/coding/Jarvis/plan.md).

### 3.1 Task States
- `[READY]` — Available for any agent with the appropriate domain role to claim.
- `[CLAIMED: <AgentName>]` — Claimed by an active agent; locked files are strictly off-limits to others.
- `[IN_PROGRESS: <AgentName>]` — Active implementation and testing in progress.
- `[BLOCKED: <Reason>]` — Blocked pending another task's completion or user clarification.
- `[DONE]` — Verified, smoke-tested, change log appended, locks released.

### 3.2 Locking Procedure
1. Search [plan.md](file:///m:/coding/Jarvis/plan.md) for the target Task ID (e.g. `TASK-04`).
2. Verify that none of the files listed under `Target Files` are currently claimed by another agent.
3. Update the task status:
   ```markdown
   | TASK-04 | Replace Playwright search with ddgs | tools.py | ⚡ Tool Agent | [CLAIMED: Antigravity] |
   ```
4. Perform the code edits.
5. Run the required verification tests.
6. Update the task status to `[DONE]` and append an entry to the Change Log in `plan.md`.

---

## 4. Conflict Resolution & Rollback Protocol

### 4.1 Broken Contracts or Failed Tests
If an agent makes a change that breaks any of the verification suites:
1. Do NOT leave the codebase broken.
2. Revert the file immediately:
   ```powershell
   git checkout -- path/to/file.py
   ```
3. If an automated backup was created in `.jarvis_backups/`, use `restore_backup(filename)`.
4. Log the failure in [plan.md](file:///m:/coding/Jarvis/plan.md) under the task notes and mark status as `[BLOCKED]`.

### 4.2 Handling Overlapping Dependencies
If Agent A (working on `tools.py`) needs a function exposed to Agent B (working on `llm.py`):
1. Agent A completes the `tools.py` function and tests it standalone.
2. Agent A logs the completion in `plan.md` with the exact function signature and sample return value.
3. Agent B reads `plan.md`, pulls the update, and binds the tool into `llm.py:available_tools`.

---

## 5. Agent Verification Checklist

Every agent must complete this checklist before marking any task as `[DONE]`:

- [ ] All new and modified Python files pass `python -m py_compile <path>`.
- [ ] No `input()` calls remain on execution paths accessible by the GUI server or background agents.
- [ ] No hardcoded temporary file collisions (e.g. static `temp.wav` or `screenshot.png` without unique timestamps or in-memory buffers).
- [ ] Flash Tier (`qwen2.5:3b`) residency (`keep_alive=-1`) and Pro/Vision offload (`keep_alive=0`) remain intact.
- [ ] Audio models remain pinned to CPU (`device="cpu"`, `compute_type="int8"`).
- [ ] All relevant test scripts (`test_voiceos.py`, `test_gui.py`, `tier_smoke_test.py`) exit with code 0.
- [ ] Change Log entry appended to [plan.md](file:///m:/coding/Jarvis/plan.md).

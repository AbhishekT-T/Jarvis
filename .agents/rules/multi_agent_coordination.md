# Multi-Agent Coordination & Safety Rules

Every agent operating in this repository must adhere to the following rules:

## 1. Mandatory Context Ingestion
Before making changes to any file:
- Read `agents.md` for domain ownership, hardware invariants, and tool standards.
- Read `plan.md` to identify active tasks and check file locks.
- Read `ARCHITECTURE.md` to ensure your changes adhere to public interfaces, database schemas, and REST contracts.

## 2. Task Claiming & File Locking
- Never edit a file currently marked `[CLAIMED: ...]` or `[IN_PROGRESS: ...]` by another agent in `plan.md`.
- Claim your target task by setting its status to `[CLAIMED: <YourAgentName>]` in `plan.md`.
- Keep diffs focused strictly on the files owned by your domain role.

## 3. Hardware & Residency Invariants (Never Violate)
- **Flash Tier (`qwen2.5:3b`):** Must remain resident (`keep_alive=-1`) in GPU VRAM (`num_gpu=-1`).
- **Pro Tier (`qwen3-coder:30b`):** Must run on CPU (`num_gpu=0`) and unload immediately (`keep_alive=0`).
- **Vision Tier (`gemma4:e4b`):** Must unload immediately (`keep_alive=0`).
- **Audio Stack:** Must run on CPU (`device="cpu"`, `compute_type="int8"`). Never route audio to GPU.
- **Environment:** Always use `jarvis_project/.venv`. Never create new virtual environments.

## 4. Quality Gate & Logging
Before marking your task `[DONE]`:
1. Verify syntax: `python -m py_compile <modified_file.py>`
2. Run test suites:
   - `python test_gui.py` (if GUI or API touched)
   - `python test_voiceos.py` (if window context or automation touched)
   - `python tier_smoke_test.py` (if models or tools touched)
3. Append a structured entry to the Change Log in `plan.md`.
4. Release the file lock by updating the task status in `plan.md`.

## 5. Always Push to GitHub (Mandatory)
Every agent MUST push its changes to GitHub immediately upon completing and verifying any task:
1. Stage changes: `git add <files>`
2. Commit with a concise descriptive message: `git commit -m "feat/fix: ..."`
3. Push to remote: `git push origin main` (or active feature branch)
Never leave verified work uncommitted or unpushed.


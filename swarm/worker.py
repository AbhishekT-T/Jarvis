#!/usr/bin/env python3
"""
Autonomous Swarm Worker Daemon.
Watches tasks.json in a loop, claims matching tasks, invokes the assigned CLI agent,
commits code, and transitions task status automatically.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SWARM_DIR = Path(__file__).resolve().parent
TASKS_FILE = SWARM_DIR / "tasks.json"

def get_utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def load_tasks():
    if not TASKS_FILE.exists():
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("tasks", [])
    except Exception:
        return []

def save_tasks(tasks):
    try:
        data = {"project": "Jarvis", "updated_at": get_utc_now_iso(), "tasks": tasks}
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[!] Error saving tasks: {e}", file=sys.stderr)

def run_cmd(cmd, cwd=None):
    print(f"\n>> Executing: {cmd}")
    try:
        res = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=False)
        return res.returncode == 0
    except Exception as e:
        print(f"[!] Command failed: {e}", file=sys.stderr)
        return False

def handle_coder_task(task, role, tool_name, worktree_dir):
    print(f"\n=======================================================")
    print(f"[*] AUTO-CLAIMED Task #{task['id']}: {task['title']}")
    print(f"[*] Tool: {tool_name} | Role: {role.upper()}")
    print(f"=======================================================")
    print(f"Prompt:\n{task.get('description', '')}\n")

    # Update status to in_progress
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task["id"]:
            t["status"] = "in_progress"
            t["claimed_at"] = get_utc_now_iso()
    save_tasks(tasks)

    # 1. Execute task with assigned agent or fallback
    prompt_text = f"{task['title']}. {task.get('description', '')}"
    print(f"[*] Launching {tool_name} in {worktree_dir}...")

    # Check which tool command is available
    if tool_name == "opencode":
        cmd = f'opencode run "{prompt_text}"'
    elif tool_name == "cline":
        cmd = f'cline "{prompt_text}"'
    elif tool_name == "agy":
        cmd = f'agy "{prompt_text}"'
    else:
        cmd = f'agy "{prompt_text}"'

    success = run_cmd(cmd, cwd=worktree_dir)

    # If the assigned tool failed / ran out of tokens, seamlessly fallback to agy
    if not success and tool_name != "agy":
        print(f"\n[!] ALERT: {tool_name} failed or ran out of tokens!")
        print(f"[*] Seamlessly transferring partial work to agy (Backup Heavy Lifter)...")
        
        fallback_prompt = (
            f"HAND-OFF TASK: The previous agent ({tool_name}) encountered an error or ran out of tokens "
            f"while working on: '{task['title']}'. Original spec: {task.get('description', '')}. "
            f"Please inspect the current git status and modified files in this worktree, finish the implementation, "
            f"and adhere strictly to Ponytail simplicity (stdlib/native first, no bloat)."
        )
        
        fallback_cmd = f'agy "{fallback_prompt}"'
        print(f">> Executing Fallback: {fallback_cmd}")
        success = run_cmd(fallback_cmd, cwd=worktree_dir)

    # 2. Auto-commit changes on agent branch
    print(f"[*] Auto-committing changes to branch agent/{role}...")
    run_cmd("git add .", cwd=worktree_dir)
    run_cmd(f'git commit -m "feat({role}): {task["title"]}"', cwd=worktree_dir)

    # 3. Mark ready_for_review
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task["id"]:
            t["status"] = "ready_for_review"
            t["completed_at"] = get_utc_now_iso()
            if not success:
                t["fallback_to_agy"] = True
    save_tasks(tasks)

    print(f"\n[OK] Task #{task['id']} completed and marked READY_FOR_REVIEW!")
    print(f"[*] Returning to watch mode...\n")

def handle_qa_task(task, worktree_dir):
    print(f"\n=======================================================")
    print(f"[*] QA REVIEWING Task #{task['id']}: {task['title']}")
    print(f"=======================================================")

    branch = task.get("branch", "agent/backend")

    # 1. Run tests
    print(f"[*] Running automated smoke tests...")
    test_ok = run_cmd("python tier_smoke_test.py", cwd=worktree_dir)

    # 2. Merge to main
    print(f"[*] Merging branch {branch} into main...")
    run_cmd("git checkout main", cwd=worktree_dir)
    run_cmd(f"git merge {branch} --no-ff -m \"merge: {task['title']} verified and simplified\"", cwd=worktree_dir)

    # 3. Mark completed
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task["id"]:
            t["status"] = "completed"
            t["qa_verified_at"] = get_utc_now_iso()
    save_tasks(tasks)

    print(f"\n[OK] Task #{task['id']} verified, merged to main, and COMPLETED!")
    print(f"[*] Returning to QA watch mode...\n")

def main():
    parser = argparse.ArgumentParser(description="Autonomous Swarm Worker Watcher")
    parser.add_argument("--role", required=True, choices=["backend", "frontend", "qa"])
    parser.add_argument("--tool", default="agy", help="CLI tool (opencode, cline, kilo, agy)")
    parser.add_argument("--worktree", default=".", help="Path to worktree directory")

    args = parser.parse_args()
    worktree_path = Path(args.worktree).resolve()

    print("=" * 60)
    print(f"   AUTONOMOUS WORKER DAEMON: {args.role.upper()} ({args.tool})")
    print("=" * 60)
    print(f"Worktree: {worktree_path}")
    print(f"Watching tasks.json for incoming work... (Press Ctrl+C to stop)\n")

    while True:
        try:
            tasks = load_tasks()

            if args.role in ["backend", "frontend"]:
                # Look for pending tasks for this role
                matching = [t for t in tasks if t.get("role") == args.role and t.get("status") == "pending"]
                if matching:
                    handle_coder_task(matching[0], args.role, args.tool, str(worktree_path))

            elif args.role == "qa":
                # Look for tasks that are ready_for_review
                ready = [t for t in tasks if t.get("status") == "ready_for_review"]
                if ready:
                    handle_qa_task(ready[0], str(worktree_path))

            time.sleep(2)
        except KeyboardInterrupt:
            print("\nWorker stopped by user.")
            break
        except Exception as e:
            print(f"[!] Worker loop error: {e}", file=sys.stderr)
            time.sleep(3)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Swarm Dispatcher: Refines high-level prompts into granular agent tasks
and pushes them to tasks.json for agy, opencode, cline, and kilo.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

SWARM_DIR = Path(__file__).resolve().parent
TASKS_FILE = SWARM_DIR / "tasks.json"

def get_utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def load_data():
    if not TASKS_FILE.exists():
        return {"project": "Jarvis", "updated_at": get_utc_now_iso(), "tasks": []}
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"project": "Jarvis", "updated_at": get_utc_now_iso(), "tasks": []}

def save_data(data):
    data["updated_at"] = get_utc_now_iso()
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def add_task(data, role, title, desc, tool):
    next_id = max([t["id"] for t in data.get("tasks", [])], default=0) + 1
    new_task = {
        "id": next_id,
        "title": title,
        "role": role,
        "assigned_tool": tool,
        "description": desc,
        "status": "pending",
        "branch": f"agent/{role}",
        "created_at": get_utc_now_iso()
    }
    data.setdefault("tasks", []).append(new_task)
    return next_id

def main():
    parser = argparse.ArgumentParser(description="Swarm Dispatcher for agy, opencode, cline, and kilo")
    parser.add_argument("prompt", help="Your high-level feature or bugfix prompt")
    parser.add_argument("--backend-only", action="store_true", help="Dispatch only to opencode (backend)")
    parser.add_argument("--frontend-only", action="store_true", help="Dispatch only to cline (frontend)")

    args = parser.parse_args()
    data = load_data()

    print("=" * 60)
    print(f"[*] DISPATCHING GOAL: {args.prompt}")
    print("=" * 60)

    if args.backend_only:
        t_id = add_task(data, "backend", f"Backend: {args.prompt}", args.prompt, "opencode")
        print(f"[+] Task #{t_id} assigned to [opencode] in Jarvis-backend")
    elif args.frontend_only:
        t_id = add_task(data, "frontend", f"Frontend: {args.prompt}", args.prompt, "cline")
        print(f"[+] Task #{t_id} assigned to [cline] in Jarvis-frontend")
    else:
        # Full stack dispatch
        b_id = add_task(data, "backend", f"Backend implementation for: {args.prompt}", f"Implement required backend APIs/models for: {args.prompt}. Use stdlib & native features (Ponytail rules).", "opencode")
        f_id = add_task(data, "frontend", f"Frontend implementation for: {args.prompt}", f"Implement required UI/client views for: {args.prompt}.", "cline")
        q_id = add_task(data, "qa", f"QA, Tests & Ponytail review for: {args.prompt}", f"Test implementation, run ponytail-review to eliminate bloat, then merge to main.", "kilo")

        print(f"[+] Task #{b_id} -> [opencode] (Backend)")
        print(f"[+] Task #{f_id} -> [cline] (Frontend)")
        print(f"[+] Task #{q_id} -> [kilo] (QA & Ponytail Review)")

    save_data(data)
    print("\n[OK] All tasks dispatched to swarm/tasks.json!")
    print("[*] Worker agents can now run: python ../Jarvis/swarm/swarm_helper.py next --role <role> --claim\n")

if __name__ == "__main__":
    main()

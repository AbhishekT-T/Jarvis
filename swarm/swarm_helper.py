#!/usr/bin/env python3
"""
Swarm Helper: Blackboard task coordinator for multi-agent CLI workflows.
Allows agents and humans to safely query, add, claim, and update tasks in tasks.json.
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Locate tasks.json in repo root/swarm/tasks.json or search upwards
def find_tasks_file() -> Path:
    current = Path(__file__).resolve().parent
    tasks_path = current / "tasks.json"
    if tasks_path.exists():
        return tasks_path
    
    # Check parent dirs
    for parent in current.parents:
        candidate = parent / "swarm" / "tasks.json"
        if candidate.exists():
            return candidate
        candidate2 = parent / "tasks.json"
        if candidate2.exists():
            return candidate2

    return tasks_path

TASKS_FILE = find_tasks_file()

def get_utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def load_data():
    if not TASKS_FILE.exists():
        return {"project": "Jarvis", "updated_at": get_utc_now_iso(), "tasks": []}
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {TASKS_FILE}: {e}", file=sys.stderr)
        return {"project": "Jarvis", "updated_at": get_utc_now_iso(), "tasks": []}

def save_data(data):
    data["updated_at"] = get_utc_now_iso()
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def cmd_add(args):
    data = load_data()
    next_id = max([t["id"] for t in data.get("tasks", [])], default=0) + 1
    new_task = {
        "id": next_id,
        "title": args.title,
        "role": args.role.lower(),
        "description": args.desc or "",
        "status": "pending",
        "branch": f"agent/{args.role.lower()}",
        "created_at": get_utc_now_iso()
    }
    data.setdefault("tasks", []).append(new_task)
    save_data(data)
    print(f"[+] Created Task #{next_id}: [{new_task['role'].upper()}] {new_task['title']}")

def cmd_list(args):
    data = load_data()
    tasks = data.get("tasks", [])
    if args.role:
        tasks = [t for t in tasks if t.get("role") == args.role.lower()]
    if args.status:
        tasks = [t for t in tasks if t.get("status") == args.status.lower()]

    if not tasks:
        print("No tasks found matching criteria.")
        return

    print(f"\n{'ID':<4} {'ROLE':<10} {'STATUS':<18} {'TITLE'}")
    print("=" * 60)
    for t in tasks:
        status_color = t.get("status", "pending")
        print(f"{t['id']:<4} {t.get('role', ''):<10} {status_color:<18} {t.get('title', '')}")
    print()

def cmd_next(args):
    data = load_data()
    role = args.role.lower()
    pending = [t for t in data.get("tasks", []) if t.get("role") == role and t.get("status") == "pending"]
    if not pending:
        print(f"No pending tasks for role: {role}")
        return

    task = pending[0]
    if args.claim:
        task["status"] = "in_progress"
        task["claimed_at"] = get_utc_now_iso()
        save_data(data)
        print(f"[CLAIMED] Task #{task['id']}: {task['title']}")
    else:
        print(f"[NEXT AVAILABLE] Task #{task['id']}: {task['title']}")
    
    print(f"\nDescription:\n{task.get('description', '(No description)')}\n")

def cmd_status(args):
    data = load_data()
    found = False
    for t in data.get("tasks", []):
        if t["id"] == args.id:
            old_status = t.get("status")
            t["status"] = args.status.lower()
            t["updated_at"] = get_utc_now_iso()
            if args.notes:
                t["notes"] = args.notes
            save_data(data)
            print(f"[OK] Task #{args.id} status changed: {old_status} -> {args.status.lower()}")
            found = True
            break
    if not found:
        print(f"Task #{args.id} not found.", file=sys.stderr)

def cmd_get(args):
    data = load_data()
    for t in data.get("tasks", []):
        if t["id"] == args.id:
            print(json.dumps(t, indent=2))
            return
    print(f"Task #{args.id} not found.", file=sys.stderr)

def cmd_clear(args):
    if not args.yes:
        print("Pass --yes to confirm clearing all completed tasks.")
        return
    data = load_data()
    data["tasks"] = [t for t in data.get("tasks", []) if t.get("status") != "completed"]
    save_data(data)
    print("Cleared completed tasks from blackboard.")

def main():
    parser = argparse.ArgumentParser(description="Swarm Helper: Multi-Agent Blackboard CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = subparsers.add_parser("add", help="Add a task to the queue")
    p_add.add_argument("--role", required=True, choices=["backend", "frontend", "qa", "all"], help="Assignee role")
    p_add.add_argument("--title", required=True, help="Short task summary")
    p_add.add_argument("--desc", default="", help="Detailed specs / requirements")
    p_add.set_defaults(func=cmd_add)

    # list
    p_list = subparsers.add_parser("list", help="List tasks")
    p_list.add_argument("--role", choices=["backend", "frontend", "qa"], help="Filter by role")
    p_list.add_argument("--status", choices=["pending", "in_progress", "ready_for_review", "completed"], help="Filter by status")
    p_list.set_defaults(func=cmd_list)

    # next
    p_next = subparsers.add_parser("next", help="Get next pending task for a role")
    p_next.add_argument("--role", required=True, choices=["backend", "frontend", "qa"], help="Your role")
    p_next.add_argument("--claim", action="store_true", help="Automatically claim task and set to in_progress")
    p_next.set_defaults(func=cmd_next)

    # set-status
    p_stat = subparsers.add_parser("set-status", help="Update task status")
    p_stat.add_argument("--id", type=int, required=True, help="Task ID")
    p_stat.add_argument("--status", required=True, choices=["pending", "in_progress", "ready_for_review", "completed"], help="New status")
    p_stat.add_argument("--notes", default="", help="Optional notes or summary")
    p_stat.set_defaults(func=cmd_status)

    # get
    p_get = subparsers.add_parser("get", help="Get details for a task ID")
    p_get.add_argument("--id", type=int, required=True, help="Task ID")
    p_get.set_defaults(func=cmd_get)

    # clear
    p_clr = subparsers.add_parser("clear", help="Clear completed tasks")
    p_clr.add_argument("--yes", action="store_true", help="Confirm clear")
    p_clr.set_defaults(func=cmd_clear)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()

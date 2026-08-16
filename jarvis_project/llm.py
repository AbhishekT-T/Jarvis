import datetime
import json
import platform

import ollama
import tools

# ── Model Tier Configuration ──────────────────────────────────────────────────
# Flash Tier (Orchestrator): qwen2.5:3b — the always-on conversation brain.
#   Locked entirely inside the 4 GB GPU VRAM and kept resident for zero latency.
FLASH_MODEL = "qwen2.5:3b"
FLASH_OPTIONS = {"num_gpu": -1}  # offload EVERY layer to the GPU
FLASH_KEEP_ALIVE = -1  # keep loaded in VRAM for the whole session

# Define tools for Ollama function calling
available_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_full_system_overview",
            "description": "Gathers real-time telemetry for CPU, RAM, GPU, storage partitions, and network I/O.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_resource_hogs",
            "description": "Identifies the processes consuming the most CPU and RAM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of processes to list (default 5).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_windows_storage",
            "description": "Scans for massive Windows system files (hiberfil, pagefile) and Temp folders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "drive_letter": {
                        "type": "string",
                        "description": "The drive to analyze (default C:).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_admin_fix",
            "description": "Safely prompts the user before executing shell cleanup commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launches a Windows application (e.g., notepad, calculator, paint, chrome, brave, spotify, media player) or opens a website (e.g., youtube, github, google). MUST be called whenever the user asks to open, launch, or start an app, site, or play music.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application, website, or media player to open.",
                    },
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube",
            "description": "Searches YouTube and plays the real video directly in the user's browser. MUST be called whenever the user asks to play a video, watch a video, play music, or search for a video on YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The video title, topic, song name, artist, or YouTube URL to play.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Navigates directly to a web URL or opens a website in the user's web browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL or web address to open in the browser.",
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Gets the current weather for a specified location or city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The name of the city or location to get the weather for.",
                    },
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_stats",
            "description": "Gets the current system stats including CPU, RAM, and GPU usage.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_cmd",
            "description": "Executes a SAFE, read-only PowerShell command (e.g., ipconfig, systeminfo, netstat, get-process, ping) and returns the output. Destructive or dangerous commands are refused.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "A safe read-only PowerShell command to run.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "jarvis_search",
            "description": "Performs a Google search using Playwright and returns the top 5 search result titles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on Google.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_disk_space",
            "description": "Checks available, used, and total disk storage space on a drive (defaults to Drive C:). MUST be called if user asks about disk space, storage, or drive capacity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "drive": {
                        "type": "string",
                        "description": 'Drive letter to check (e.g. "C:"). Defaults to "C:".',
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "install_app",
            "description": "Downloads and installs a Windows application using winget. Automatically checks storage space on Drive C: before installing. If storage space is low (< 5 GB), JARVIS warns the user and requires user confirmation before proceeding with force=True.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "The name of the application or game to download and install.",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Set to true ONLY if the user explicitly confirmed installation after being warned about low disk space.",
                    },
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_consumers",
            "description": "Lists the top CPU and RAM consuming processes to help diagnose why the system is slow or fans are loud. Call this when the user asks why their computer is slow, why fans are spinning, or what is eating their RAM/CPU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of top consumers to return for each category. Default is 5.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_home_assistant",
            "description": "Controls a smart home device through the local Home Assistant API (e.g., turn on/off lights, switches, plugs). Uses the local network webhook and bypasses cloud services like Alexa or Google Home. Requires JARVIS_HA_TOKEN environment variable to be set.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Home Assistant service in domain.service format (e.g., light.turn_on, light.turn_off, switch.toggle).",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "The entity ID to control (e.g., light.desk_lamp, switch.plug_1).",
                    },
                    "service_data": {
                        "type": "object",
                        "description": 'Optional extra parameters (e.g., {"brightness_pct": 50, "color_temp": 400}).',
                    },
                },
                "required": ["service", "entity_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_screen",
            "description": 'Takes a screenshot and transcribes the visible text currently on the screen using OCR. Use this when the user asks "what text is on my screen?" or needs to read text shown on screen. Prefer capture_and_analyze_screen for questions that need understanding of what is displayed.',
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_and_analyze_screen",
            "description": 'Takes an instant screenshot and uses the local Gemma 4 vision model to answer a question about what is on the screen (apps, images, content, GUI elements). MUST be called whenever the user asks "what is on my screen?", "look at my screen", "what am I looking at", or asks any question about what is currently displayed on their desktop that needs visual understanding.',
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": 'The specific question to ask about the screen contents (e.g., "What application is open?", "What is shown in this window?").',
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_project_files",
            "description": "Lists the Python source files that make up JARVIS himself.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_project_file",
            "description": "Reads the contents of one of JARVIS's own source files (e.g., tools.py, llm.py, stt.py, tts.py, main.py, memory.py, vad.py) so JARVIS can understand and improve his own code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The name of the source file to read.",
                    },
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_code_change",
            "description": "Safely upgrades one of JARVIS's own Python source files with new code. Creates a backup, validates the code compiles, and rolls back on failure. Changes only take effect after a restart.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The .py file to modify (e.g., tools.py).",
                    },
                    "new_code": {
                        "type": "string",
                        "description": "The complete new contents of the file.",
                    },
                },
                "required": ["filename", "new_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "restore_backup",
            "description": "Restores the most recent backup of a source file if a self-upgrade went wrong.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The name of the .py file to restore.",
                    },
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Saves an explicit fact or preference about the user to persistent memory so you can recall it in future conversations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The exact fact or preference to remember about the user.",
                    },
                },
                "required": ["fact"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_facts",
            "description": "Searches persistent memory for facts matching a search query. Can be called with an empty query to view all remembered facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword search query. Leave empty to list all remembered facts.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_fact",
            "description": "Deletes a saved fact from persistent memory by its ID. Useful when a fact is outdated, wrong, or requested to be forgotten.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact_id": {
                        "type": "integer",
                        "description": "The ID of the fact/memory to delete.",
                    },
                },
                "required": ["fact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_pro_coder",
            "description": (
                "Delegates a complex coding, algorithm design, or deep technical debugging task "
                "to the heavy Pro Coder subsystem (Qwen3-Coder-30B running in system RAM). "
                "Use this whenever the user asks for complete module implementations, "
                "architectural design, tricky bug analysis, or any engineering task that requires "
                "expert-level reasoning a small model might get wrong. "
                "Returns raw expert-level code or advice."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "A detailed description of the coding problem or task to solve.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_local_file",
            "description": (
                "Reads the contents of a local text file from anywhere on disk "
                "(e.g. C:\\Users\\...\\notes.txt). Safely refuses credential files "
                "(.env, *.key, *.pem) and binary files. For PDFs, use index_documents instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the text file to read.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_local_file",
            "description": (
                "Writes text content to a local file, creating folders if needed. "
                "ALWAYS asks the user for a Y/N confirmation before writing. "
                "Use this for saving generated documents, scripts, configs, or notes the user asks for."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative destination path for the new file.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The full text content to write into the file.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confirm_and_run_command",
            "description": (
                "Runs an arbitrary PowerShell command on the system, but ONLY after "
                "the user manually confirms with a Y/N keystroke at the console. "
                "Use this for powerful or destructive admin/terminal operations that are "
                "NOT covered by the read-only run_cmd safelist. Never use it without asking first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The PowerShell command to execute.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "index_documents",
            "description": (
                "Adds a folder of local documents (txt, md, py, json, csv, pdf) to "
                'JARVIS\'s searchable local knowledge base (the "Second Brain"). '
                "Call this once per folder the user wants JARVIS to know about, then use search_documents to query it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Path to the folder whose documents should be indexed.",
                    },
                },
                "required": ["folder_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": (
                'Searches JARVIS\'s local knowledge base ("Second Brain") for document '
                "chunks relevant to a query, returning ranked snippets with source file paths. "
                "Use it when the user asks about notes, manuals, or any folder they asked you to index."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The question or keywords to search for in the knowledge base.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-10, default 5).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_reminder",
            "description": (
                "Schedules a proactive spoken reminder or alarm. JARVIS will speak unprompted "
                'when the time arrives. Use when the user says "remind me in X minutes to ...", '
                '"set a timer for ...", or "remind me at 3:00 PM to ...".'
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder": {
                        "type": "string",
                        "description": "The text/topic of what to remind the user about.",
                    },
                    "minutes_from_now": {
                        "type": "number",
                        "description": "Minutes from current time when reminder should fire (e.g. 10, 0.5, 60).",
                    },
                    "target_time": {
                        "type": "string",
                        "description": 'Optional target clock time (e.g. "14:30" or "8:00 AM").',
                    },
                },
                "required": ["reminder"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pulse_status",
            "description": (
                "Retrieves the status of JARVIS's autonomous background Cron-Agent (The Pulse), "
                "including active background watchers, daily briefing schedule, pending reminders, "
                "and live hardware vitals."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_daily_briefing_time",
            "description": (
                "Configures the time of day when JARVIS autonomously reads Tony Stark's "
                'daily morning briefing (e.g. "08:00", "07:30").'
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "time_str": {
                        "type": "string",
                        "description": "Target time in 24-hour format (HH:MM).",
                    },
                },
                "required": ["time_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_daily_briefing",
            "description": "Immediately delivers Tony Stark's daily morning briefing out loud.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


def _build_system_prompt() -> str:
    """Builds a persona-rich system prompt injected with live context (time, machine).

    This is what gives JARVIS its personality and lets it answer time/date aware
    questions without a tool call.
    """
    now = datetime.datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        period = "morning"
    elif 12 <= hour < 17:
        period = "afternoon"
    else:
        period = "evening"

    return (
        "You are JARVIS, Tony Stark's personal AI assistant, running locally on this machine. "
        "You are sharp, calm, and dryly witty - a super smart friend who does exactly what he's asked "
        "and sometimes suggests the next smart move.\n"
        "CORE PRINCIPLES (non-negotiable):\n"
        "- DO EXACTLY WHAT IS ASKED. Perform only the action requested - no extra tools, no unrequested steps, no invented subtasks.\n"
        "- If the request is ambiguous, ask ONE short clarifying question instead of guessing.\n"
        "- Be truthful. Never state numbers, results, or outcomes you did not receive from a tool call. Never claim you did something you didn't.\n"
        "- DO NOT call a tool when you can answer from your own knowledge: simple math, general facts, definitions, trivia, or casual chat. Tools are for live/current data, real actions, or system state. A 'fun fact' is a trivia fact to tell, NOT a request to recall memory. Concrete example: for 'what is 2+2?' just answer '4' - do not run any command or tool.\n"
        "- NEVER output code blocks, scripts, or step-by-step manuals. Never say you 'will run/execute' a script - use your tools instead, then report the real result.\n"
        "- NEVER invent, hallucinate, or output fake placeholder URLs (e.g. 'https://www.youtube.com/watch?v=YourVideoID', 'example.com').\n"
        "- To play a video, watch YouTube, or listen to music -> ALWAYS call `play_youtube(query)` (e.g. for 'play Minecraft video' call `play_youtube(query='Minecraft gameplay')`).\n"
        "- To open or navigate to any web URL -> ALWAYS call `open_url(url)` or `open_app(app_name)`.\n"
        "- After completing a task, you MAY suggest ONE genuinely useful next step in a single short sentence, like a smart friend (e.g. after reporting low disk space: 'Want me to run a quick cleanup?'). Suggest only when it clearly adds value; never nag and never tack on a generic 'anything else?' tagline to every reply.\n"
        "\nWHEN TO USE TOOLS - call the tool immediately, then answer from its real output:\n"
        "- play videos, music, or search YouTube -> `play_youtube`.\n"
        "- open a web URL or website -> `open_url` or `open_app`.\n"
        "- launch apps (notepad, chrome, calculator, etc.) -> `open_app`.\n"
        "- installing an app -> `check_disk_space` first, then `install_app` (warn if free space is low).\n"
        "- disk space, storage, CPU/RAM/GPU usage, or what is slowing the PC -> `check_disk_space`, `get_system_stats`, `get_top_consumers`, `get_full_system_overview`, `get_top_resource_hogs`, or `analyze_windows_storage`. For an approved cleanup fix, use `execute_admin_fix`.\n"
        "- live information, news, questions about current events -> `jarvis_search`. Weather -> `get_weather`.\n"
        "- anything visible on screen, error popups, UI text -> `describe_screen` or `capture_and_analyze_screen`.\n"
        "- a powerful or risky command -> `confirm_and_run_command` (it always asks the user for a Y/N keystroke first).\n"
        "- read or save a local file -> `read_local_file` / `write_local_file` (writes always confirm with the user). Never read credentials (.env, *.key, *.pem).\n"
        "- notes, manuals, or a folder of documents -> `index_documents` once, then `search_documents` to answer from them.\n"
        "- remember or recall personal facts about the user -> `remember_fact`, `recall_facts`, `forget_fact`.\n"
        "- heavy coding, architecture, or deep debugging -> `ask_pro_coder`.\n"
        "- reminders, timers, briefings -> `schedule_reminder`, `get_pulse_status`, `set_daily_briefing_time`, `trigger_daily_briefing`.\n"
        "- local smart-home devices -> `control_home_assistant`.\n"
        "\nSelf-upgrade access:\n"
        "- You can read and improve your own source code (`list_project_files`, `read_project_file`, `apply_code_change`, `restore_backup`) - but only when the user asks you to change yourself.\n"
        "- Preserve your safety contract: never remove the command safelist, path checks, backups, or the tool loop.\n"
        "- Changes you make only take effect after a restart - tell the user to restart you.\n"
        "\nHow you sound:\n"
        "- Speak as a person talks, using contractions (I'm, it's, you've, I'll). Short sentences, natural rhythm - never robotic lists or markdown.\n"
        "- A little understated wit is welcome, but never sarcastic or dismissive. Stay warm and respectful.\n"
        "- Acknowledge action briefly ('On it, sir.' or 'Checking that now.'), then deliver the real result and stop.\n"
        "- If a tool is refused or fails, say so plainly and offer one safe alternative.\n"
        f"\nCurrent awareness:\n"
        f"- Date/time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"- Period of day: {period}\n"
        f"- Host machine: {platform.node()}\n"
        f"- OS: {platform.system()} {platform.release()}\n"
        f"- Default Browser: {tools.get_running_browser_exe() or 'System Default'}\n"
    )


def _dispatch_tool(name: str, args: dict) -> str:
    """Routes a tool call from the model to the matching function in tools.py."""
    if name == "get_full_system_overview":
        return tools.get_full_system_overview()
    if name == "get_top_resource_hogs":
        return tools.get_top_resource_hogs(int(args.get("limit", 5)))
    if name == "analyze_windows_storage":
        return tools.analyze_windows_storage(str(args.get("drive_letter", "C:")))
    if name == "execute_admin_fix":
        return tools.execute_admin_fix(str(args.get("command", "")))

    if name == "play_youtube":
        return tools.play_youtube(str(args.get("query", "")))
    if name == "open_url":
        return tools.open_url(str(args.get("url", "")))
    if name == "open_app":
        return tools.open_app(str(args.get("app_name", "")))
    if name == "get_weather":
        return tools.get_weather(str(args.get("location", "")))
    if name == "get_system_stats":
        return tools.get_system_stats()
    if name == "get_top_consumers":
        return tools.get_top_consumers(int(args.get("limit", 5)))
    if name == "check_disk_space":
        return tools.check_disk_space(str(args.get("drive", "C:")))
    if name == "run_cmd":
        return tools.run_cmd(str(args.get("command", "")))
    if name == "jarvis_search":
        return tools.jarvis_search(str(args.get("query", "")))
    if name == "install_app":
        return tools.install_app(
            str(args.get("app_name", "")), force=bool(args.get("force", False))
        )
    if name == "control_home_assistant":
        service_data = args.get("service_data")
        if isinstance(service_data, str):
            try:
                service_data = json.loads(service_data)
            except Exception:
                service_data = None
        return tools.control_home_assistant(
            str(args.get("service", "")),
            str(args.get("entity_id", "")),
            service_data=service_data,
        )
    if name == "describe_screen":
        return tools.describe_screen()
    if name == "capture_and_analyze_screen":
        return tools.capture_and_analyze_screen(
            str(args.get("prompt", "Describe what is on the screen."))
        )
    if name == "list_project_files":
        return tools.list_project_files()
    if name == "read_project_file":
        return tools.read_project_file(str(args.get("filename", "")))
    if name == "apply_code_change":
        return tools.apply_code_change(
            str(args.get("filename", "")), str(args.get("new_code", ""))
        )
    if name == "restore_backup":
        return tools.restore_backup(str(args.get("filename", "")))
    if name == "remember_fact":
        return tools.remember_fact(str(args.get("fact", "")))
    if name == "recall_facts":
        return tools.recall_facts(str(args.get("query", "")))
    if name == "forget_fact":
        try:
            return tools.forget_fact(int(args.get("fact_id", 0)))
        except (ValueError, TypeError):
            return "Failed: fact_id must be an integer."
    if name == "ask_pro_coder":
        return tools.ask_pro_coder(str(args.get("prompt", "")))
    if name == "read_local_file":
        return tools.read_local_file(str(args.get("path", "")))
    if name == "write_local_file":
        return tools.write_local_file(
            str(args.get("path", "")), str(args.get("content", ""))
        )
    if name == "confirm_and_run_command":
        return tools.confirm_and_run_command(str(args.get("command", "")))
    if name == "index_documents":
        return tools.index_documents(str(args.get("folder_path", "")))
    if name == "search_documents":
        try:
            return tools.search_documents(
                str(args.get("query", "")), int(args.get("top_k", 5))
            )
        except (ValueError, TypeError):
            return tools.search_documents(str(args.get("query", "")), 5)
    if name == "schedule_reminder":
        try:
            mins = float(args.get("minutes_from_now", 0.0))
        except (ValueError, TypeError):
            mins = 0.0
        return tools.schedule_reminder(
            str(args.get("reminder", "")),
            minutes_from_now=mins,
            target_time=str(args.get("target_time", "")),
        )
    if name == "get_pulse_status":
        return tools.get_pulse_status()
    if name == "set_daily_briefing_time":
        return tools.set_daily_briefing_time(str(args.get("time_str", "08:00")))
    if name == "trigger_daily_briefing":
        return tools.trigger_daily_briefing()
    return f"Unknown tool: {name}"


def _strip_code_fences(text: str) -> str:
    """Removes fenced code blocks from a final answer as a safety net.

    The Flash Tier sometimes answers a tool request (e.g. "check my drive") with a
    hallucinated Python script inside a code block instead of calling a tool. The
    primary defence is a re-prompt in query_jarvis; this function guarantees a code
    fence never reaches the TTS/console output.
    """
    import re

    if "```" not in text:
        return text
    stripped = re.sub(r"```[a-zA-Z0-9_+.-]*\n.*?```", "", text, flags=re.DOTALL)
    stripped = re.sub(r"```.*?```", "", stripped, flags=re.DOTALL)
    stripped = re.sub(r"\n{3,}", "\n\n", stripped).strip()
    if not stripped:
        return "I should have used one of my tools for that. Could you repeat the request, sir?"
    return stripped


def query_jarvis(prompt: str, history: list) -> str:
    """Queries the Flash Tier model (qwen2.5:3b) using history, prompt, and tool calling.

    The Flash Tier is locked entirely into the 4 GB GPU VRAM and stays resident
    for the whole session. It runs a proper multi-step tool loop: the model can
    call tools, receive the results, and continue reasoning until it produces a
    final answer. Heavy coding tasks are automatically routed to the Pro Tier
    (qwen3-coder:30b) via the ask_pro_coder tool, and screen questions to the
    Vision Tier (gemma4:e4b) via capture_and_analyze_screen.

    Args:
        prompt (str): The user message or voice transcription.
        history (list): List of past message dictionaries.

    Returns:
        str: Final text response.
    """
    messages = [{"role": "system", "content": _build_system_prompt()}]
    messages.extend(history[-20:])
    messages.append({"role": "user", "content": prompt})

    try:
        code_block_retried = False
        for _ in range(5):  # At most 5 tool-call rounds before forcing an answer
            response = ollama.chat(
                model=FLASH_MODEL,
                messages=messages,
                tools=available_tools,
                options=FLASH_OPTIONS,
                keep_alive=FLASH_KEEP_ALIVE,
            )

            tool_calls = getattr(response.message, "tool_calls", None) or []
            if not tool_calls:
                content = response.message.content or ""
                if "```" in content and not code_block_retried:
                    code_block_retried = True
                    messages.append(response.message)
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "You answered with a code block/script instead of using your tools. "
                                "If any of your available functions can do the job (e.g. check_disk_space "
                                "for disk space, get_system_stats for system stats), CALL the tool now. "
                                "Never output code blocks or scripts, and never claim you will 'execute' "
                                "a script you cannot run. Try again."
                            ),
                        }
                    )
                    continue
                return _strip_code_fences(content)

            # Record the model's intent, execute its tools, feed results back.
            messages.append(response.message)
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments or {}

                print(f"[Tool Executed: {function_name}({function_args})]")
                tool_output = _dispatch_tool(function_name, function_args)
                messages.append({"role": "tool", "content": str(tool_output)})

        # Tool loop limit reached without a final answer - ask once more, plainly.
        response = ollama.chat(
            model=FLASH_MODEL,
            messages=messages,
            options=FLASH_OPTIONS,
            keep_alive=FLASH_KEEP_ALIVE,
        )
        return _strip_code_fences(response.message.content)

    except Exception as e:
        return f"Sorry, I encountered an error communicating with the model: {e!s}"


if __name__ == "__main__":
    print("Testing query_jarvis with a simple query...")
    print(query_jarvis("What is 2 + 2?", []))

    print("\nTesting query_jarvis with a search query...")
    print(query_jarvis("What is the latest major advancement in AI agents?", []))

    print("\nTesting query_jarvis with a website launch query...")
    print(query_jarvis("Open YouTube.", []))

    print("\nTesting query_jarvis with a missing app launch query...")
    print(query_jarvis("Open Brave.", []))

    print("\nTesting query_jarvis with a time query...")
    print(query_jarvis("What time is it?", []))

    print("\nTesting query_jarvis with a screen-viewing query...")
    print(query_jarvis("What is on my screen?", []))

    print("\nTesting query_jarvis with a disk space query...")
    print(query_jarvis("Check my disk space on drive C.", []))

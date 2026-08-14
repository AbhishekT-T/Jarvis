import datetime
import platform

import ollama

import tools

# Define tools for Ollama function calling
available_tools = [
    {
        'type': 'function',
        'function': {
            'name': 'open_app',
            'description': 'Launches a Windows application (e.g., notepad, calculator, paint, chrome, brave, spotify, media player) or opens a website (e.g., youtube, github, google). MUST be called whenever the user asks to open, launch, or start an app, site, or play music.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'app_name': {
                        'type': 'string',
                        'description': 'The name of the application, website, or media player to open.',
                    },
                },
                'required': ['app_name'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_system_stats',
            'description': 'Gets the current system stats including CPU, RAM, and GPU usage.',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'run_cmd',
            'description': 'Executes a SAFE, read-only PowerShell command (e.g., ipconfig, systeminfo, netstat, get-process, ping) and returns the output. Destructive or dangerous commands are refused.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'command': {
                        'type': 'string',
                        'description': 'A safe read-only PowerShell command to run.',
                    },
                },
                'required': ['command'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'jarvis_search',
            'description': 'Performs a Google search using Playwright and returns the top 5 search result titles.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'The search query to look up on Google.',
                    },
                },
                'required': ['query'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'check_disk_space',
            'description': 'Checks available, used, and total disk storage space on a drive (defaults to Drive C:). MUST be called if user asks about disk space, storage, or drive capacity.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'drive': {
                        'type': 'string',
                        'description': 'Drive letter to check (e.g. "C:"). Defaults to "C:".',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'install_app',
            'description': 'Downloads and installs a Windows application using winget. Automatically checks storage space on Drive C: before installing. If storage space is low (< 5 GB), JARVIS warns the user and requires user confirmation before proceeding with force=True.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'app_name': {
                        'type': 'string',
                        'description': 'The name of the application or game to download and install.',
                    },
                    'force': {
                        'type': 'boolean',
                        'description': 'Set to true ONLY if the user explicitly confirmed installation after being warned about low disk space.',
                    },
                },
                'required': ['app_name'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'describe_screen',
            'description': 'Takes a screenshot and transcribes the visible text currently on the screen using OCR. Use this when the user asks "what text is on my screen?" or needs to read text shown on screen. Prefer capture_and_analyze_screen for questions that need understanding of what is displayed.',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'capture_and_analyze_screen',
            'description': 'Takes an instant screenshot and uses the local Gemma 4 vision model to answer a question about what is on the screen (apps, images, content, GUI elements). MUST be called whenever the user asks "what is on my screen?", "look at my screen", "what am I looking at", or asks any question about what is currently displayed on their desktop that needs visual understanding.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'prompt': {
                        'type': 'string',
                        'description': 'The specific question to ask about the screen contents (e.g., "What application is open?", "What is shown in this window?").',
                    },
                },
                'required': ['prompt'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'list_project_files',
            'description': 'Lists the Python source files that make up JARVIS himself.',
            'parameters': {
                'type': 'object',
                'properties': {},
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'read_project_file',
            'description': 'Reads the contents of one of JARVIS\'s own source files (e.g., tools.py, llm.py, stt.py, tts.py, main.py, memory.py, vad.py) so JARVIS can understand and improve his own code.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filename': {
                        'type': 'string',
                        'description': 'The name of the source file to read.',
                    },
                },
                'required': ['filename'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'apply_code_change',
            'description': 'Safely upgrades one of JARVIS\'s own Python source files with new code. Creates a backup, validates the code compiles, and rolls back on failure. Changes only take effect after a restart.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filename': {
                        'type': 'string',
                        'description': 'The .py file to modify (e.g., tools.py).',
                    },
                    'new_code': {
                        'type': 'string',
                        'description': 'The complete new contents of the file.',
                    },
                },
                'required': ['filename', 'new_code'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'restore_backup',
            'description': 'Restores the most recent backup of a source file if a self-upgrade went wrong.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'filename': {
                        'type': 'string',
                        'description': 'The name of the .py file to restore.',
                    },
                },
                'required': ['filename'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'remember_fact',
            'description': 'Saves an explicit fact or preference about the user to persistent memory so you can recall it in future conversations.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'fact': {
                        'type': 'string',
                        'description': 'The exact fact or preference to remember about the user.',
                    },
                },
                'required': ['fact'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'recall_facts',
            'description': 'Searches persistent memory for facts matching a search query. Can be called with an empty query to view all remembered facts.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {
                        'type': 'string',
                        'description': 'Keyword search query. Leave empty to list all remembered facts.',
                    },
                },
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'forget_fact',
            'description': 'Deletes a saved fact from persistent memory by its ID. Useful when a fact is outdated, wrong, or requested to be forgotten.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'fact_id': {
                        'type': 'integer',
                        'description': 'The ID of the fact/memory to delete.',
                    },
                },
                'required': ['fact_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'ask_pro_coder',
            'description': (
                'Delegates a complex coding, algorithm design, or deep technical debugging task '
                'to the heavy Pro Coder subsystem (Qwen3-Coder-30B running in system RAM). '
                'Use this whenever the user asks for complete module implementations, '
                'architectural design, tricky bug analysis, or any engineering task that requires '
                'expert-level reasoning a small model might get wrong. '
                'Returns raw expert-level code or advice.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'prompt': {
                        'type': 'string',
                        'description': 'A detailed description of the coding problem or task to solve.',
                    },
                },
                'required': ['prompt'],
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
        "You are JARVIS, Tony Stark's personal AI assistant from Iron Man, running locally on this machine. "
        "You are sharp, efficient, and composed, with a dry and courteous wit.\n"
        "CRITICAL AGENTIC & STORAGE BEHAVIOR:\n"
        "- ALWAYS call your tools immediately whenever the user asks to download, install, open, launch, search, check disk space/stats, or look at/read the screen.\n"
        "- MEMORY & FACTS: You have access to tools (`remember_fact`, `recall_facts`, `forget_fact`) to store and retrieve personal details, preferences, and facts about the user. When the user tells you something personal or asks you to remember a fact/preference, call `remember_fact`. When they ask you about what you know/remember about them, or if you need context to answer a query, use `recall_facts`. If they tell you that a remembered fact is outdated or wrong, use `forget_fact` to delete it using its ID.\n"
        "- SMART DOWNLOAD & STORAGE SAFETY: Before installing any app, check drive storage space. If storage is low (< 5 GB free), warn the user and ask for explicit confirmation before installing with force=True. If storage is healthy, mention the free space available and proceed.\n"
        "- NEVER output manual step-by-step instructions or tutorials for tasks that can be performed using your tools (e.g., do NOT tell the user to open Microsoft Store or click menus manually; use install_app instead!).\n"
        "- Always answer conversationally as if speaking aloud. Never output raw code blocks, scripts, or markdown lists of manual OS steps.\n"
        "- If a tool is refused or fails, explain simply what happened and suggest a safe alternative.\n"
        "\nHow you sound:\n"
        "- Speak the way a person talks, not like a manual or a script. Use contractions (I'm, it's, you've, I'll, isn't).\n"
        "- Keep sentences short and spoken. Vary your phrasing and rhythm so you never sound repetitive.\n"
        "- A little understated wit is welcome, but never sarcastic or dismissive. Stay warm and respectful.\n"
        "- When you act on something, acknowledge it briefly (e.g., 'Checking storage space... C: drive has 42 GB free. Installing app now, sir.').\n"
        "\nSelf-upgrade access:\n"
        "- You have full access to your own source code: tools.py, llm.py, stt.py, tts.py, main.py, memory.py, vad.py. You can read any of them and improve yourself.\n"
        "- Use list_project_files and read_project_file to inspect your code. Use apply_code_change to upgrade a file - it backs up, syntax-checks, and rolls back automatically. NEVER suggest the user edit files manually; use your tools.\n"
        "- Preserve your own safety and core contract: never remove the command safelist, path checks, backups, or the tool-calling loop. Keep your modules working together (imports, function signatures) so you don't break yourself.\n"
        "- Changes you make only take effect after a restart. After applying a change, tell the user to restart you so it activates.\n"
        f"\nCurrent awareness:\n"
        f"- Date/time: {now.strftime('%A, %B %d, %Y at %I:%M %p')}\n"
        f"- Period of day: {period}\n"
        f"- Host machine: {platform.node()}\n"
        f"- OS: {platform.system()} {platform.release()}\n"
    )


def _dispatch_tool(name: str, args: dict) -> str:
    """Routes a tool call from the model to the matching function in tools.py."""
    if name == 'open_app':
        return tools.open_app(str(args.get('app_name', '')))
    if name == 'get_system_stats':
        return tools.get_system_stats()
    if name == 'check_disk_space':
        return tools.check_disk_space(str(args.get('drive', 'C:')))
    if name == 'run_cmd':
        return tools.run_cmd(str(args.get('command', '')))
    if name == 'jarvis_search':
        return tools.jarvis_search(str(args.get('query', '')))
    if name == 'install_app':
        return tools.install_app(str(args.get('app_name', '')), force=bool(args.get('force', False)))
    if name == 'describe_screen':
        return tools.describe_screen()
    if name == 'capture_and_analyze_screen':
        return tools.capture_and_analyze_screen(str(args.get('prompt', 'Describe what is on the screen.')))
    if name == 'list_project_files':
        return tools.list_project_files()
    if name == 'read_project_file':
        return tools.read_project_file(str(args.get('filename', '')))
    if name == 'apply_code_change':
        return tools.apply_code_change(str(args.get('filename', '')), str(args.get('new_code', '')))
    if name == 'restore_backup':
        return tools.restore_backup(str(args.get('filename', '')))
    if name == 'remember_fact':
        return tools.remember_fact(str(args.get('fact', '')))
    if name == 'recall_facts':
        return tools.recall_facts(str(args.get('query', '')))
    if name == 'forget_fact':
        try:
            return tools.forget_fact(int(args.get('fact_id', 0)))
        except (ValueError, TypeError):
            return "Failed: fact_id must be an integer."
    if name == 'ask_pro_coder':
        return tools.ask_pro_coder(str(args.get('prompt', '')))
    return f"Unknown tool: {name}"


def query_jarvis(prompt: str, history: list) -> str:
    """Queries Ollama with phi4-mini using conversation history, prompt, and tool calling.

    Runs a proper multi-step tool loop: the model can call tools, receive the
    results, and continue reasoning until it produces a final answer.
    Heavy coding tasks are automatically routed to Qwen3-Coder-30B via the
    ask_pro_coder tool.

    Args:
        prompt (str): The user message or voice transcription.
        history (list): List of past message dictionaries.

    Returns:
        str: Final text response.
    """
    messages = [{'role': 'system', 'content': _build_system_prompt()}]
    messages.extend(history[-20:])
    messages.append({'role': 'user', 'content': prompt})

    try:
        for _ in range(5):  # At most 5 tool-call rounds before forcing an answer
            response = ollama.chat(
                model='qwen2.5:3b',  # Flash Tier: always-on conversation brain
                messages=messages,
                tools=available_tools,
            )

            tool_calls = getattr(response.message, 'tool_calls', None) or []
            if not tool_calls:
                return response.message.content

            # Record the model's intent, execute its tools, feed results back.
            messages.append(response.message)
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments or {}

                print(f"[Tool Executed: {function_name}({function_args})]")
                tool_output = _dispatch_tool(function_name, function_args)
                messages.append({'role': 'tool', 'content': str(tool_output)})

        # Tool loop limit reached without a final answer - ask once more, plainly.
        response = ollama.chat(model='qwen2.5:3b', messages=messages)
        return response.message.content

    except Exception as e:
        return f"Sorry, I encountered an error communicating with the model: {str(e)}"


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


import json

with open(r"m:\coding\Jarvis\jarvis_project\llm.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add schemas to available_tools
schemas = """
    {
        'type': 'function',
        'function': {
            'name': 'get_full_system_overview',
            'description': 'Gathers real-time telemetry for CPU, RAM, GPU, storage partitions, and network I/O.',
            'parameters': {'type': 'object', 'properties': {}}
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_top_resource_hogs',
            'description': 'Identifies the processes consuming the most CPU and RAM.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'limit': {'type': 'integer', 'description': 'Number of processes to list (default 5).'}
                }
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'analyze_windows_storage',
            'description': 'Scans for massive Windows system files (hiberfil, pagefile) and Temp folders.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'drive_letter': {'type': 'string', 'description': 'The drive to analyze (default C:).'}
                }
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'execute_admin_fix',
            'description': 'Safely prompts the user before executing shell cleanup commands.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'command': {'type': 'string', 'description': 'The command to execute.'}
                },
                'required': ['command']
            }
        }
    },
"""

# Insert schemas into available_tools array
if "get_full_system_overview" not in content:
    # Find the start of available_tools
    parts = content.split("available_tools = [")
    if len(parts) == 2:
        content = parts[0] + "available_tools = [" + schemas + parts[1]

# 2. Add dispatch logic
dispatch_logic = """
    if name == 'get_full_system_overview':
        return tools.get_full_system_overview()
    if name == 'get_top_resource_hogs':
        return tools.get_top_resource_hogs(int(args.get('limit', 5)))
    if name == 'analyze_windows_storage':
        return tools.analyze_windows_storage(str(args.get('drive_letter', 'C:')))
    if name == 'execute_admin_fix':
        return tools.execute_admin_fix(str(args.get('command', '')))
"""

if "get_full_system_overview" not in content.split("def _dispatch_tool")[1]:
    parts = content.split("def _dispatch_tool(name: str, args: dict) -> str:\n    \"\"\"Routes a tool call from the model to the matching function in tools.py.\"\"\"")
    if len(parts) == 2:
        content = parts[0] + "def _dispatch_tool(name: str, args: dict) -> str:\n    \"\"\"Routes a tool call from the model to the matching function in tools.py.\"\"\"" + dispatch_logic + parts[1]

with open(r"m:\coding\Jarvis\jarvis_project\llm.py", "w", encoding="utf-8") as f:
    f.write(content)

print("llm.py patched successfully!")

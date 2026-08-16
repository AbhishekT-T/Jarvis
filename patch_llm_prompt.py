with open(r"m:\coding\Jarvis\jarvis_project\llm.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the SYSTEM DIAGNOSIS line
old_line = "why their fans are loud, why the system is slow, or what is eating CPU/RAM, call `get_top_consumers` to identify the heaviest processes."
new_line = "why their fans are loud, why the system is slow, or what is eating CPU/RAM, call `get_full_system_overview` and `get_top_resource_hogs`. For deep storage analysis, use `analyze_windows_storage`. If a cleanup command is needed, ALWAYS use `execute_admin_fix` to prompt the user before executing."

content = content.replace(old_line, new_line)

with open(r"m:\coding\Jarvis\jarvis_project\llm.py", "w", encoding="utf-8") as f:
    f.write(content)

print("llm.py prompt patched!")

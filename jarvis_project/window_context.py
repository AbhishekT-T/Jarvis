"""Window Context Inspector for VoiceOS.

Detects the foreground active window, process name, window title, and classifies
the target application to inform context-aware speech dictation and action routing.
"""

from typing import Any
import psutil
import win32gui
import win32process


APP_CATEGORIES = {
    # Coding / IDEs / Editors
    "code.exe": ("VS Code", "coding"),
    "cursor.exe": ("Cursor", "coding"),
    "pycharm64.exe": ("PyCharm", "coding"),
    "idea64.exe": ("IntelliJ IDEA", "coding"),
    "sublime_text.exe": ("Sublime Text", "coding"),
    "notepad++.exe": ("Notepad++", "coding"),
    "devenv.exe": ("Visual Studio", "coding"),
    "clion64.exe": ("CLion", "coding"),
    # Communication / Chat
    "slack.exe": ("Slack", "chat"),
    "discord.exe": ("Discord", "chat"),
    "teams.exe": ("Microsoft Teams", "chat"),
    "ms-teams.exe": ("Microsoft Teams", "chat"),
    "telegram.exe": ("Telegram", "chat"),
    "whatsapp.exe": ("WhatsApp", "chat"),
    # Email
    "outlook.exe": ("Outlook", "email"),
    "thunderbird.exe": ("Thunderbird", "email"),
    "mailspring.exe": ("Mailspring", "email"),
    # Terminal / CLI
    "windowsterminal.exe": ("Windows Terminal", "terminal"),
    "powershell.exe": ("PowerShell", "terminal"),
    "pwsh.exe": ("PowerShell 7", "terminal"),
    "cmd.exe": ("Command Prompt", "terminal"),
    "mintty.exe": ("Git Bash", "terminal"),
    "alacritty.exe": ("Alacritty", "terminal"),
    "wezterm-gui.exe": ("WezTerm", "terminal"),
    # Documents / Notes
    "winword.exe": ("Microsoft Word", "document"),
    "excel.exe": ("Microsoft Excel", "document"),
    "powerpnt.exe": ("Microsoft PowerPoint", "document"),
    "onenote.exe": ("OneNote", "document"),
    "notion.exe": ("Notion", "document"),
    "obsidian.exe": ("Obsidian", "document"),
    "notepad.exe": ("Notepad", "document"),
    # Browsers
    "chrome.exe": ("Google Chrome", "browser"),
    "brave.exe": ("Brave", "browser"),
    "msedge.exe": ("Microsoft Edge", "browser"),
    "firefox.exe": ("Firefox", "browser"),
    "opera.exe": ("Opera", "browser"),
}


def _classify_window(
    process_name: str, title: str
) -> tuple[str, str]:
    """Classifies an application based on process executable name and window title."""
    proc_lower = process_name.lower().strip()
    title_lower = title.lower().strip()

    # Direct process lookup
    if proc_lower in APP_CATEGORIES:
        app_name, category = APP_CATEGORIES[proc_lower]
        # Browser sub-classification based on active tab / title
        if category == "browser":
            if any(k in title_lower for k in ["gmail", "outlook", "mail", "inbox"]):
                return f"{app_name} (Webmail)", "email"
            if any(k in title_lower for k in ["slack", "discord", "whatsapp", "teams", "messages"]):
                return f"{app_name} (Web Chat)", "chat"
            if any(k in title_lower for k in ["docs.google", "google docs", "notion", "confluence"]):
                return f"{app_name} (Web Docs)", "document"
            if any(k in title_lower for k in ["github", "gitlab", "stackoverflow", "pull request", "pr #"]):
                return f"{app_name} (Dev)", "coding"
        return app_name, category

    # Title-based fallback
    if any(k in title_lower for k in ["visual studio code", "cursor", "sublime", "pycharm"]):
        return "Code Editor", "coding"
    if any(k in title_lower for k in ["outlook", "thunderbird", "mail"]):
        return "Email Client", "email"
    if any(k in title_lower for k in ["slack", "discord", "teams", "whatsapp"]):
        return "Chat App", "chat"
    if any(k in title_lower for k in ["word", "notepad", "obsidian", "notion", "docs"]):
        return "Document Editor", "document"
    if any(k in title_lower for k in ["powershell", "cmd", "terminal", "bash"]):
        return "Terminal", "terminal"

    return process_name or "Unknown Application", "general"


def get_active_window_context() -> dict[str, Any]:
    """Inspects and returns metadata for the currently focused foreground window."""
    hwnd = 0
    title = ""
    process_name = ""
    pid = 0

    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and win32gui.IsWindowVisible(hwnd):
            raw_title = win32gui.GetWindowText(hwnd).strip()
            if raw_title:
                title = raw_title
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid > 0:
                    proc = psutil.Process(pid)
                    process_name = proc.name()
            except Exception:
                process_name = ""
    except Exception:
        pass

    # If foreground window has no title or is a shell container, inspect visible top-level windows
    if not title or title in ["Program Manager", "Start", "Windows Input Experience"]:
        candidates: list[tuple[int, str, str, int]] = []

        def enum_cb(h: int, _: Any) -> bool:
            try:
                if win32gui.IsWindowVisible(h):
                    t = win32gui.GetWindowText(h).strip()
                    if t and t not in ["Program Manager", "Start", "Windows Input Experience"]:
                        p_name = ""
                        p_id = 0
                        try:
                            _, p_id = win32process.GetWindowThreadProcessId(h)
                            if p_id > 0:
                                p_name = psutil.Process(p_id).name()
                        except Exception:
                            pass
                        candidates.append((h, t, p_name, p_id))
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
            if candidates:
                # Pick the first non-shell candidate
                hwnd, title, process_name, pid = candidates[0]
        except Exception:
            pass

    app_name, category = _classify_window(process_name, title)

    return {
        "hwnd": hwnd,
        "title": title or "Unknown",
        "process_name": process_name or "unknown.exe",
        "app_name": app_name,
        "category": category,
    }

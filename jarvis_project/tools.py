import subprocess
import psutil
import shutil
import webbrowser
import os
import re
import datetime
import base64
import winreg
import mss
import mss.tools
from PIL import ImageGrab
import win32gui
from playwright.sync_api import sync_playwright
import memory

VISION_MODEL = "moondream"

def find_app_path(executable_name: str) -> str | None:
    """Finds the absolute path of an executable by searching PATH, Registry, and standard folders.
    """
    if not executable_name.endswith(".exe"):
        executable_name += ".exe"

    # 1. Search in PATH
    path = shutil.which(executable_name)
    if path:
        return path
        
    # 2. Search in Windows Registry (App Paths)
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            key_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\{executable_name}"
            with winreg.OpenKey(hive, key_path) as key:
                path, _ = winreg.QueryValueEx(key, "")
                if path:
                    path = path.strip('"')
                    if os.path.exists(path):
                        return path
        except OSError:
            continue

    # 3. Search in standard installation directories
    user_profile = os.environ.get("USERPROFILE", "")
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    
    search_dirs = [
        program_files,
        program_files_x86,
        local_app_data,
        os.path.join(user_profile, "AppData", "Local")
    ]
    
    subpaths = {
        "brave.exe": [
            "BraveSoftware\\Brave-Browser\\Application\\brave.exe",
        ],
        "chrome.exe": [
            "Google\\Chrome\\Application\\chrome.exe",
        ],
        "msedge.exe": [
            "Microsoft\\Edge\\Application\\msedge.exe",
        ]
    }
    
    if executable_name in subpaths:
        for base_dir in search_dirs:
            for subpath in subpaths[executable_name]:
                full_path = os.path.join(base_dir, subpath)
                if os.path.exists(full_path):
                    return full_path
                    
    return None

def get_running_browser_exe() -> str | None:
    """Scans running processes to find if a known browser is active, and returns its executable path.
    """
    known_browsers = ["brave.exe", "chrome.exe", "msedge.exe", "firefox.exe"]
    for proc in psutil.process_iter(['name', 'exe']):
        try:
            name = proc.info['name']
            if name:
                name_lower = name.lower()
                if name_lower in known_browsers:
                    exe_path = proc.info['exe']
                    if exe_path and os.path.exists(exe_path):
                        return exe_path
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None

def open_app(app_name: str) -> str:
    """Launches a Windows application or opens a website in the default browser.
    
    Args:
        app_name (str): The name of the application or website to open.
        
    Returns:
        str: Status message indicating success or failure.
    """
    app_name_lower = app_name.lower().strip(" ,.?!")
    
    # Map friendly website names to URLs
    web_map = {
        "youtube": "https://www.youtube.com",
        "google": "https://www.google.com",
        "github": "https://www.github.com",
        "gmail": "https://mail.google.com",
        "reddit": "https://www.reddit.com",
        "wikipedia": "https://www.wikipedia.org"
    }
    
    # Check if app_name is a URL or a mapped website name
    if app_name_lower.startswith(("http://", "https://", "www.")) or app_name_lower in web_map:
        url = web_map.get(app_name_lower, app_name_lower)
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        # Only allow well-formed http/https URLs with no whitespace or quotes
        if not re.match(r"^https?://[^\s\"']+$", url, re.IGNORECASE):
            return f"Failed to open website. Invalid URL: {url}"
        try:
            # Check if any browser is already running
            running_browser_exe = get_running_browser_exe()
            if running_browser_exe:
                # Open URL specifically in the running browser.
                # Args as a list (no shell) prevents command injection via the URL.
                subprocess.Popen([running_browser_exe, url])
                return f"Successfully opened website {url} in running browser: {os.path.basename(running_browser_exe)}"
            else:
                # Fallback to the system default browser (no shell involved)
                webbrowser.open(url)
                return f"Successfully opened website: {url}"
        except Exception as e:
            return f"Failed to open website {url}. Error: {str(e)}"
            
    # Map friendly app names to actual executables
    app_map = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "chrome": "chrome.exe",
        "brave": "brave.exe",
        "breathe": "brave.exe",  # Handle STT mis-transcription of 'Brave'
        "edge": "msedge.exe",
        "music": "wmplayer.exe",
        "media player": "wmplayer.exe",
        "wmplayer": "wmplayer.exe",
        "roblox": "RobloxPlayerBeta.exe"
    }
    
    executable = app_map.get(app_name_lower, app_name_lower)
    if not executable.endswith(".exe"):
        executable += ".exe"
    
    # Validate if executable exists in system PATH or registry (unless it's a known mapped system executable)
    is_known_system_app = app_name_lower in ["notepad", "calculator", "calc", "paint", "cmd", "powershell", "music", "media player", "wmplayer"]
    
    resolved_path = executable
    if not is_known_system_app:
        path = find_app_path(executable)
        if path:
            resolved_path = path
        else:
            return f"Failed to launch '{app_name}'. The application is not installed or not in the system PATH."
            
    if not re.match(r"^[\w.\- ]+\.exe$", executable, re.IGNORECASE):
        return f"Failed to launch '{app_name}'. Invalid application name."

    try:
        # Launch WITHOUT a shell to prevent command injection.
        # Passing args as a list (not a string) means spaces in paths are handled safely.
        subprocess.Popen([resolved_path])
        return f"Successfully launched {app_name}."
    except Exception as e:
        return f"Failed to launch {app_name}. Error: {str(e)}"

def get_system_stats() -> str:
    """Gets the current CPU, RAM, and GPU usage.
    
    Returns:
        str: System stats information.
    """
    cpu_usage = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent
    
    gpu_stats = "GPU: Not available or not NVIDIA"
    if shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,utilization.memory", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True
            )
            out = res.stdout.strip().split(',')
            if len(out) >= 2:
                gpu_util = out[0].strip()
                gpu_mem_util = out[1].strip()
                gpu_stats = f"GPU Utilization: {gpu_util}%, GPU Memory utilization: {gpu_mem_util}%"
        except Exception:
            pass
            
    return f"CPU Usage: {cpu_usage}%, RAM Usage: {ram_usage}%, {gpu_stats}"

SAFE_COMMAND_PREFIXES = (
    "get-", "select-", "where-", "ipconfig", "systeminfo", "netstat", "whoami",
    "ping ", "pathping ", "tracert ", "dir ", "ls ", "echo ", "hostname",
    "tasklist", "ver", "cls", "clear", "pwd", "cd ", "help", "get-date",
    "get-time", "get-process", "get-service", "get-childitem", "get-command",
    "get-volume", "get-psdrive", "measure-command", "test-connection",
)

BLOCKED_TOKENS = (
    "remove-item", "rm ", "del ", "erase ", "format ", "format-volume",
    "clear-disk", "new-partition", "remove-partition", "shutdown", "restart-computer",
    "stop-computer", "restart-service", "stop-service", "taskkill", "kill ",
    "stop-process", "set-itemproperty", "set-executionpolicy", "reg delete",
    "reg add", "reg import", "net user", "net localgroup", "net share",
    "net stop", "net start", "wmic", "schtasks", "bcdedit", "diskpart",
    "attrib ", "start-process", "invoke-expression", "iex ", "enable-",
    "disable-", "install-", "uninstall-", "clear-", ">", ">>", "|", ";",
    "&&", "||", "& ", "del /", "rd /", "rmdir",
)

def run_cmd(command: str) -> str:
    """Executes a PowerShell command and returns the output.

    Security: only allows a safelist of read-only/informational commands.
    Destructive or dangerous commands are refused before execution.

    Args:
        command (str): The powershell command to execute.

    Returns:
        str: Standard output, standard error, or a refusal message.
    """
    command = command.strip()
    if not command:
        return "Refused: no command provided."

    lower_cmd = command.lower()
    blocked = [tok for tok in BLOCKED_TOKENS if tok in lower_cmd]
    if blocked:
        return (f"Refused: command contains blocked tokens ({', '.join(blocked)}). "
                f"Only safe read-only commands are permitted.")

    if not lower_cmd.startswith(SAFE_COMMAND_PREFIXES):
        return (f"Refused: '{command}' is not on the safelist. "
                f"Ask the user for approval before running arbitrary commands.")

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, timeout=15
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += "\nErrors:\n" + result.stderr
        return output.strip() if output.strip() else "[Command executed with no output]"
    except subprocess.TimeoutExpired:
        return "Refused: command timed out."
    except Exception as e:
        return f"Failed to execute command. Error: {str(e)}"

def jarvis_search(query: str) -> str:
    """Performs a Google search using Playwright and returns the top 5 result titles.
    
    Args:
        query (str): The search query.
        
    Returns:
        str: A list or text summary of the top search results.
    """
    try:
        with sync_playwright() as p:
            # headless=False allows you to physically watch JARVIS control the browser
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # Navigate to Google
            page.goto("https://www.google.com")
            
            # Locate the search bar, fill it, and hit Enter
            search_box = page.locator("textarea[name='q']")
            search_box.fill(query)
            search_box.press("Enter")
            
            # Wait for the results to load
            page.wait_for_selector("h3")
            
            # Scrape the top 5 result titles to feed back to the AI
            results = page.locator("h3").all_inner_texts()
            browser.close()
            
            top_results = [r.strip() for r in results if r.strip()][:5]
            if not top_results:
                return "No search results found."
            return "\n".join(f"- {title}" for title in top_results)
    except Exception as e:
        return f"Error executing search: {str(e)}"

def check_disk_space(drive: str = "C:") -> str:
    """Checks and returns the total, used, and free disk space for a drive.
    
    Args:
        drive (str): The drive letter (e.g., "C:"). Defaults to "C:".
        
    Returns:
        str: Disk space status message.
    """
    try:
        drive_path = drive.strip().upper()
        if len(drive_path) == 1:
            drive_path += ":\\"
        elif not drive_path.endswith("\\"):
            drive_path += "\\"
        total, used, free = shutil.disk_usage(drive_path)
        gb = 1024 ** 3
        return f"Drive {drive_path[0]}: Total: {total/gb:.1f} GB, Used: {used/gb:.1f} GB, Free: {free/gb:.1f} GB."
    except Exception as e:
        return f"Could not check disk space for drive '{drive}': {str(e)}"


def install_app(app_name: str, force: bool = False) -> str:
    """Uses Windows Package Manager (winget) to install an application securely and interactively,
    after checking drive storage space.
    
    Args:
        app_name (str): The name of the application to install.
        force (bool): Set to True if user explicitly confirmed installation despite low space.
        
    Returns:
        str: Status message indicating storage check, success, or failure.
    """
    app_name_clean = app_name.strip(" ,.?!")
    if not re.match(r"^[\w\s.\-]+$", app_name_clean):
        return f"Refused to install '{app_name}': invalid characters in application name."
    
    # Check storage space before proceeding
    try:
        _, _, free = shutil.disk_usage("C:\\")
        free_gb = free / (1024 ** 3)
    except Exception:
        free_gb = 999.0
        
    LOW_SPACE_THRESHOLD_GB = 5.0
    if free_gb < LOW_SPACE_THRESHOLD_GB and not force:
        return (f"Storage Alert: Drive C: has only {free_gb:.1f} GB free (below {LOW_SPACE_THRESHOLD_GB} GB limit). "
                f"Please ask the user for explicit confirmation before installing '{app_name}'.")
    
    # Check if winget is available
    if not shutil.which("winget"):
        return "Windows Package Manager (winget) is not installed on this system. Cannot perform automatic installations."
        
    try:
        # Search for the package first to retrieve the exact package ID
        search_cmd = f'winget search "{app_name_clean}"'
        search_res = subprocess.run(
            ["powershell", "-Command", search_cmd],
            capture_output=True, text=True, timeout=15
        )
        
        lines = search_res.stdout.splitlines()
        app_id = None
        
        # Parse search output for ID (lines[2] onwards are actual search results)
        for line in lines[2:]:
            parts = [p.strip() for p in line.split(" ") if p.strip()]
            if len(parts) >= 2:
                # Retrieve the package ID (second column); only accept safe ID chars
                candidate_id = parts[1]
                if re.match(r"^[\w.\-]+$", candidate_id):
                    app_id = candidate_id
                    break
                
        # Launch winget in a separate visible CMD window to prevent blocking on UAC/admin prompts
        if app_id:
            install_cmd = f'start cmd /c "echo Installing {app_id}... && winget install --id {app_id} --accept-source-agreements --accept-package-agreements && pause"'
            target = app_id
        else:
            install_cmd = f'start cmd /c "echo Installing {app_name_clean}... && winget install --name \\"{app_name_clean}\\" --accept-source-agreements --accept-package-agreements && pause"'
            target = app_name_clean
            
        subprocess.Popen(install_cmd, shell=True)
        
        return (f"Checked disk space: Drive C: has {free_gb:.1f} GB free. "
                f"I have launched the installer window for '{app_name}' (ID/Name: {target}), sir. "
                f"Please approve the administrator prompt if it appears to complete installation.")
        
    except Exception as e:
        return f"Failed to start installer for '{app_name}'. Error: {str(e)}"


def describe_screen() -> str:
    """Takes a screenshot, performs OCR on the image using Windows' native OCR engine,
    and retrieves the active window's title.
    
    Returns:
        str: A description of what is currently on the screen.
    """
    temp_filename = "screenshot.png"
    try:
        # 1. Capture the screen using Pillow
        screenshot = ImageGrab.grab()
        screenshot.save(temp_filename)
        
        # 2. Get active window title
        active_window_title = "Unknown"
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                active_window_title = title
                
        # Fallback to topmost visible application window if active title is empty or system-level
        if active_window_title in ["Unknown", "Program Manager", "Start", "Windows Input Experience", ""]:
            def enum_windows_callback(h, l):
                nonlocal active_window_title
                if win32gui.IsWindowVisible(h):
                    t = win32gui.GetWindowText(h).strip()
                    # Skip common shell / desktop background containers
                    if t and t not in ["Program Manager", "Start", "Windows Input Experience", ""]:
                        active_window_title = t
                        return False  # Stop enumeration
                return True
            try:
                win32gui.EnumWindows(enum_windows_callback, None)
            except Exception:
                pass
            
        # 3. Use Windows' native OCR engine via PowerShell
        ocr_script = """
        [void][Windows.Security.Credentials.WebAccountProvider, Windows.Security.Credentials, ContentType=WindowsRuntime]
        [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
        [void][Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime]
        [void][System.IO.File, System.IO, ContentType=WindowsRuntime]

        $file = Get-Item "screenshot.png"
        $stream = [Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
        $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
        $writer = [System.IO.BinaryWriter]::new($stream.AsStreamForWrite())
        $writer.Write($bytes)
        $writer.Flush()
        $stream.Seek(0)

        $decoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
        while ($decoder.Status -eq 'Started') { Start-Sleep -Milliseconds 10 }
        $bitmap = $decoder.GetResults().GetSoftwareBitmapAsync()
        while ($bitmap.Status -eq 'Started') { Start-Sleep -Milliseconds 10 }

        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
        $ocrResult = $engine.RecognizeAsync($bitmap.GetResults())
        while ($ocrResult.Status -eq 'Started') { Start-Sleep -Milliseconds 10 }

        $text = $ocrResult.GetResults().Text
        Write-Output $text
        """
        
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ocr_script],
            capture_output=True, text=True, timeout=20
        )
        
        screen_text = result.stdout.strip()
        
        return (
            f"Active Window: {active_window_title}\n"
            f"Visible Screen Text (OCR):\n"
            f"{screen_text if screen_text else '[No text detected on screen]'}"
        )
        
    except Exception as e:
        return f"Failed to capture or read screen. Error: {str(e)}"
    finally:
        # Clean up temporary screenshot
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass

def _get_active_window_title() -> str:
    """Returns the title of the currently focused window, or 'Unknown'."""
    title = "Unknown"
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd).strip()
            if t and t not in ["Program Manager", "Start", "Windows Input Experience"]:
                title = t
    except Exception:
        pass
    return title

def _moondream_prompt(question: str) -> str:
    """Rewrites the user's question into a phrasing Moondream reliably answers.

    Moondream (1.8B) is trained mostly on captioning/description tasks and
    returns an empty response for some question phrasings, so generic screen
    questions are normalized to a description prompt it handles well.
    """
    q = question.lower().strip(" ,.?!")
    generic = (
        "what is on my screen", "what's on my screen", "what is shown on my screen",
        "what am i looking at", "what am i seeing", "look at my screen",
        "look at the screen", "read my screen", "what is displayed on my screen",
        "what is currently on my screen", "what is open on my screen",
    )
    if any(k in q for k in generic):
        return "Describe this screen in detail."
    return question


def _ask_vision_model(prompt: str, image_b64: str) -> str:
    """Sends one question + screenshot to the Moondream vision model and returns its text answer."""
    try:
        import ollama
    except ImportError:
        return ""
    response = ollama.chat(
        model=VISION_MODEL,
        messages=[{"role": "user", "content": prompt, "images": [image_b64]}],
    )
    return (response.message.content or "").strip()

def capture_and_analyze_screen(prompt: str) -> str:
    """Takes an instant screenshot and answers a question about it using the local Moondream vision model.

    Use this instead of describe_screen when the user asks a specific question
    about what is on the screen (not just "what text is on screen").

    Args:
        prompt (str): The question to ask the vision model about the screen contents.

    Returns:
        str: The vision model's textual answer, prefixed with the active window title.
    """
    try:
        # 1. Capture the screen instantly with mss (much faster than ImageGrab)
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            shot = sct.grab(monitor)
            png_bytes = mss.tools.to_png(shot.rgb, shot.size)
    except Exception as e:
        return f"Failed to capture screen. Error: {str(e)}"

    try:
        # 2. Encode the PNG and ask the vision model; retry with a description
        #    prompt if the model returns nothing for the user's exact question.
        image_b64 = base64.b64encode(png_bytes).decode("utf-8")
        answer = _ask_vision_model(_moondream_prompt(prompt), image_b64)
        if not answer:
            answer = _ask_vision_model("Describe this screen in detail.", image_b64)
        if not answer:
            return "The vision model could not analyze the screen. No answer was produced."

        # 3. Include the active window title so the main brain has more context.
        window_title = _get_active_window_title()
        if window_title != "Unknown":
            return f"Active Window: {window_title}\n{answer}"
        return answer
    except Exception as e:
        return (f"Failed to analyze the screen with the vision model "
                f"({VISION_MODEL}). Error: {str(e)}")

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_DIR = os.path.join(PROJECT_DIR, ".jarvis_backups")
_BLOCKED_DIRS = (".venv", "voices", "__pycache__", ".git", ".jarvis_backups")
_EDITABLE_EXTENSIONS = (".py",)


def _safe_project_path(name: str) -> str | None:
    """Resolves a file name inside the project folder, blocking path traversal."""
    full = os.path.normpath(os.path.join(PROJECT_DIR, name))
    if full != PROJECT_DIR and not full.startswith(PROJECT_DIR + os.sep):
        return None
    return full


def _is_blocked(name: str) -> bool:
    parts = name.replace("\\", "/").lower().split("/")
    return any(part in _BLOCKED_DIRS for part in parts)


def list_project_files() -> str:
    """Lists the source files JARVIS can read or modify."""
    try:
        files = sorted(
            f for f in os.listdir(PROJECT_DIR)
            if not _is_blocked(f) and f.endswith((".py", ".md"))
        )
        if not files:
            return "No editable project files found."
        return "Project files:\n" + "\n".join(f"- {f}" for f in files)
    except Exception as e:
        return f"Error listing project files: {str(e)}"


def read_project_file(filename: str) -> str:
    """Reads the contents of one of JARVIS's own source files.

    Args:
        filename (str): Name of the file inside the project folder.

    Returns:
        str: The file contents (truncated if very large).
    """
    if _is_blocked(filename):
        return f"Refused: '{filename}' is off-limits."
    full = _safe_project_path(filename)
    if full is None:
        return "Refused: invalid path."
    if not full.endswith((".py", ".md", ".txt", ".json")) or not os.path.isfile(full):
        return f"Refused: '{filename}' is not a readable source file."
    try:
        with open(full, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 12000:
            content = content[:12000] + "\n...[truncated]..."
        return f"Contents of {filename}:\n{content}"
    except Exception as e:
        return f"Error reading {filename}: {str(e)}"


def apply_code_change(filename: str, new_code: str) -> str:
    """Safely replaces the contents of a Python source file.

    Automatically backs up the original, validates the new code compiles, and
    rolls back if anything is wrong. Changes only take effect after JARVIS is
    restarted (already-loaded modules are not reloaded).

    Args:
        filename (str): The .py file to modify.
        new_code (str): The complete new contents of the file.

    Returns:
        str: Status message describing success, backup, or rejection.
    """
    if _is_blocked(filename):
        return f"Refused: '{filename}' is off-limits."
    full = _safe_project_path(filename)
    if full is None:
        return "Refused: invalid path."
    if not filename.endswith(_EDITABLE_EXTENSIONS) or not os.path.isfile(full):
        return f"Refused: '{filename}' is not an editable Python source file."

    try:
        with open(full, "r", encoding="utf-8") as f:
            original = f.read()

        os.makedirs(BACKUP_DIR, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_name = f"{stamp}_{os.path.basename(full)}"
        with open(os.path.join(BACKUP_DIR, backup_name), "w", encoding="utf-8") as f:
            f.write(original)

        with open(full, "w", encoding="utf-8") as f:
            f.write(new_code)

        import py_compile
        py_compile.compile(full, doraise=True)
    except py_compile.PyCompileError as e:
        with open(full, "w", encoding="utf-8") as f:
            f.write(original)
        return f"Change rejected and rolled back (syntax error): {e}"
    except Exception as e:
        try:
            with open(full, "w", encoding="utf-8") as f:
                f.write(original)
        except Exception:
            pass
        return f"Change rejected and rolled back: {str(e)}"

    return (f"Change applied to {filename} (backup: {backup_name}). "
            f"JARVIS must be restarted for the change to take effect.")


def restore_backup(filename: str) -> str:
    """Restores the most recent backup of a modified source file."""
    if _is_blocked(filename):
        return f"Refused: '{filename}' is off-limits."
    full = _safe_project_path(filename)
    if full is None:
        return "Refused: invalid path."
    base = os.path.basename(full)
    try:
        if not os.path.isdir(BACKUP_DIR):
            return f"No backups found for {filename}."
        matches = sorted(f for f in os.listdir(BACKUP_DIR) if f.endswith("_" + base))
        if not matches:
            return f"No backups found for {filename}."
        latest = matches[-1]
        shutil.copy2(os.path.join(BACKUP_DIR, latest), full)
        return f"Restored {filename} from backup {latest}."
    except Exception as e:
        return f"Failed to restore {filename}: {str(e)}"


def remember_fact(fact: str) -> str:
    """Saves an explicit fact or preference about the user to persistent memory.

    Args:
        fact (str): The fact to remember (e.g. "User's favorite color is blue" or "User is a software engineer").

    Returns:
        str: A message confirming the fact was remembered with its database ID.
    """
    fact = fact.strip()
    if not fact:
        return "Refused: no fact provided."
    fact_id = memory.add_fact(fact)
    if fact_id != -1:
        return f"I will remember that, sir. (Saved as memory ID {fact_id})"
    return "Failed to save the fact to my memory database."


def recall_facts(query: str = "") -> str:
    """Searches persistent memory for facts matching a search query.

    Args:
        query (str): The keyword or search query. If empty, returns all remembered facts.

    Returns:
        str: A list of matching facts or a message saying no matching memories were found.
    """
    facts = memory.get_facts(query)
    if not facts:
        if query:
            return f"I couldn't find any memories matching '{query}', sir."
        return "I don't have any facts saved in my memory database yet."
    
    lines = ["Here are the facts I recall matching your query, sir:"] if query else ["Here are all the facts I have on file, sir:"]
    for f in facts:
        lines.append(f"- ID {f['id']}: {f['fact']} (saved {f['timestamp']})")
    return "\n".join(lines)


def forget_fact(fact_id: int) -> str:
    """Deletes a saved fact from persistent memory by its ID.

    Args:
        fact_id (int): The ID of the memory/fact to delete.

    Returns:
        str: A message confirming the deletion or failure.
    """
    success = memory.delete_fact(fact_id)
    if success:
        return f"Memory ID {fact_id} has been forgotten, sir."
    return f"Failed to delete memory ID {fact_id}. Make sure the ID is correct."


if __name__ == "__main__":

    print("Testing open_app (valid app)...")
    print(open_app("notepad"))
    
    print("\nTesting open_app (website)...")
    print(open_app("youtube"))
    
    print("\nTesting open_app (missing app)...")
    print(open_app("brave"))

    print("\nTesting get_system_stats...")
    print(get_system_stats())
    
    print("\nTesting run_cmd...")
    print(run_cmd("Get-Date"))

    print("\nTesting jarvis_search...")
    print(jarvis_search("Latest advancements in AI agents"))

    print("\nTesting describe_screen...")
    print(describe_screen())


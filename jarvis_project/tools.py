import base64
import datetime
import json
import os
import re
import shutil
import subprocess
import webbrowser
import winreg
from urllib.request import Request, urlopen

import memory
import mss
import mss.tools
import ollama
import psutil
import rag
import win32gui
from PIL import ImageGrab
from playwright.sync_api import sync_playwright

# ── Model Tier Configuration ──────────────────────────────────────────────────
# Flash Tier  : qwen2.5:3b       — always-on conversation brain (4 GB GPU VRAM)
#                                 (configured in llm.py: num_gpu=-1, keep_alive=-1)
# Pro Tier    : qwen3-coder:30b  — heavy coding / algorithm tasks (System RAM, CPU).
#                                 CPU-only (num_gpu=0) + unloaded after use (keep_alive=0).
# Vision Tier : gemma4:e4b       — multimodal screen analysis (VRAM/RAM).
#                                 Unloaded after use (keep_alive=0) so it never
#                                 holds VRAM the Flash Tier needs.
VISION_MODEL = "gemma4:e4b"
PRO_CODER_MODEL = "qwen3-coder:30b"

HA_URL = os.environ.get("JARVIS_HA_URL", "http://localhost:8123")
HA_TOKEN = os.environ.get("JARVIS_HA_TOKEN", "")


def find_app_path(executable_name: str) -> str | None:
    """Finds the absolute path of an executable by searching PATH, Registry, and standard folders."""
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
        os.path.join(user_profile, "AppData", "Local"),
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
        ],
    }

    if executable_name in subpaths:
        for base_dir in search_dirs:
            for subpath in subpaths[executable_name]:
                full_path = os.path.join(base_dir, subpath)
                if os.path.exists(full_path):
                    return full_path

    return None


def get_running_browser_exe() -> str | None:
    """Scans running processes to find if a known browser is active, and returns its executable path."""
    known_browsers = ["brave.exe", "chrome.exe", "msedge.exe", "firefox.exe"]
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            name = proc.info["name"]
            if name:
                name_lower = name.lower()
                if name_lower in known_browsers:
                    exe_path = proc.info["exe"]
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
        "wikipedia": "https://www.wikipedia.org",
    }

    # Check if app_name is a URL or a mapped website name
    if (
        app_name_lower.startswith(("http://", "https://", "www."))
        or app_name_lower in web_map
    ):
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
            return f"Failed to open website {url}. Error: {e!s}"

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
        "roblox": "RobloxPlayerBeta.exe",
    }

    executable = app_map.get(app_name_lower, app_name_lower)
    if not executable.endswith(".exe"):
        executable += ".exe"

    # Validate if executable exists in system PATH or registry (unless it's a known mapped system executable)
    is_known_system_app = app_name_lower in [
        "notepad",
        "calculator",
        "calc",
        "paint",
        "cmd",
        "powershell",
        "music",
        "media player",
        "wmplayer",
    ]

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
        return f"Failed to launch {app_name}. Error: {e!s}"


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
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,utilization.memory",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            out = res.stdout.strip().split(",")
            if len(out) >= 2:
                gpu_util = out[0].strip()
                gpu_mem_util = out[1].strip()
                gpu_stats = f"GPU Utilization: {gpu_util}%, GPU Memory utilization: {gpu_mem_util}%"
        except Exception:
            pass

    return f"CPU Usage: {cpu_usage}%, RAM Usage: {ram_usage}%, {gpu_stats}"


def get_top_consumers(limit: int = 5) -> str:
    """Lists the top processes consuming CPU or RAM to diagnose system load.

    Args:
        limit (int): Number of top consumers to return for each category.

    Returns:
        str: Summary of top CPU and RAM processes with PIDs and percentages.
    """
    try:
        procs = []
        for proc in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent"]
        ):
            try:
                procs.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        top_cpu = sorted(
            procs, key=lambda p: p.get("cpu_percent", 0) or 0, reverse=True
        )[:limit]
        top_ram = sorted(
            procs, key=lambda p: p.get("memory_percent", 0) or 0, reverse=True
        )[:limit]

        lines = ["Top CPU Consumers:"]
        for p in top_cpu:
            cpu = p.get("cpu_percent", 0) or 0
            mem = p.get("memory_percent", 0) or 0
            lines.append(
                f"  PID {p['pid']}: {p['name']} — CPU {cpu:.1f}%, RAM {mem:.1f}%"
            )

        lines.append("\nTop RAM Consumers:")
        for p in top_ram:
            cpu = p.get("cpu_percent", 0) or 0
            mem = p.get("memory_percent", 0) or 0
            lines.append(
                f"  PID {p['pid']}: {p['name']} — CPU {cpu:.1f}%, RAM {mem:.1f}%"
            )

        return "\n".join(lines)
    except Exception as e:
        return f"Failed to enumerate processes: {e!s}"


SAFE_COMMAND_PREFIXES = (
    "get-",
    "select-",
    "where-",
    "ipconfig",
    "systeminfo",
    "netstat",
    "whoami",
    "ping ",
    "pathping ",
    "tracert ",
    "dir ",
    "ls ",
    "echo ",
    "hostname",
    "tasklist",
    "ver",
    "cls",
    "clear",
    "pwd",
    "cd ",
    "help",
    "get-date",
    "get-time",
    "get-process",
    "get-service",
    "get-childitem",
    "get-command",
    "get-volume",
    "get-psdrive",
    "measure-command",
    "test-connection",
)

BLOCKED_TOKENS = (
    "remove-item",
    "rm ",
    "del ",
    "erase ",
    "format ",
    "format-volume",
    "clear-disk",
    "new-partition",
    "remove-partition",
    "shutdown",
    "restart-computer",
    "stop-computer",
    "restart-service",
    "stop-service",
    "taskkill",
    "kill ",
    "stop-process",
    "set-itemproperty",
    "set-executionpolicy",
    "reg delete",
    "reg add",
    "reg import",
    "net user",
    "net localgroup",
    "net share",
    "net stop",
    "net start",
    "wmic",
    "schtasks",
    "bcdedit",
    "diskpart",
    "attrib ",
    "start-process",
    "invoke-expression",
    "iex ",
    "enable-",
    "disable-",
    "install-",
    "uninstall-",
    "clear-",
    ">",
    ">>",
    "|",
    ";",
    "&&",
    "||",
    "& ",
    "del /",
    "rd /",
    "rmdir",
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
        return (
            f"Refused: command contains blocked tokens ({', '.join(blocked)}). "
            f"Only safe read-only commands are permitted."
        )

    if not lower_cmd.startswith(SAFE_COMMAND_PREFIXES):
        return (
            f"Refused: '{command}' is not on the safelist. "
            f"Ask the user for approval before running arbitrary commands."
        )

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=15,
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
        return f"Failed to execute command. Error: {e!s}"


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
        return f"Error executing search: {e!s}"


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
        gb = 1024**3
        return f"Drive {drive_path[0]}: Total: {total / gb:.1f} GB, Used: {used / gb:.1f} GB, Free: {free / gb:.1f} GB."
    except Exception as e:
        return f"Could not check disk space for drive '{drive}': {e!s}"


def get_weather(location: str) -> str:
    """Fetches the current weather for a specific location.

    Args:
        location (str): The name of the city or location.

    Returns:
        str: Weather information.
    """
    import urllib.request
    from urllib.parse import quote

    try:
        url = f"https://wttr.in/{quote(location)}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            weather = response.read().decode("utf-8").strip()
            if weather:
                return weather
            return f"Could not retrieve weather for {location}."
    except Exception as e:
        return f"Error retrieving weather: {e!s}"


def control_home_assistant(
    service: str, entity_id: str, service_data: dict = None
) -> str:
    """Controls a Home Assistant entity via the local API (bypasses cloud).

    Requires the local Home Assistant to be reachable at JARVIS_HA_URL
    and authenticated with JARVIS_HA_TOKEN.

    Args:
        service (str): HA service in the form 'domain.service' (e.g., 'light.turn_on', 'light.turn_off', 'switch.toggle').
        entity_id (str): The target entity ID (e.g., 'light.desk_lamp').
        service_data (dict): Optional extra parameters (e.g., {'brightness_pct': 50, 'color_temp': 400}).

    Returns:
        str: Result message from Home Assistant or an error description.
    """
    if not HA_TOKEN:
        return "Refused: JARVIS_HA_TOKEN is not set. Set the JARVIS_HA_TOKEN environment variable to your Home Assistant long-lived access token."

    if "." not in service:
        return f"Refused: service must be in 'domain.service' format (e.g., 'light.turn_on'). Got: {service}"

    domain, svc = service.split(".", 1)
    payload = {"entity_id": entity_id}
    if service_data:
        payload.update(service_data)

    url = f"{HA_URL}/api/services/{domain}/{svc}"
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            try:
                result = json.loads(body)
                if isinstance(result, list) and result:
                    return f"Home Assistant accepted the command. Result: {result[0].get('entity_id', entity_id)} state={result[0].get('state', 'unknown')}."
                return f"Home Assistant accepted the command for {entity_id}."
            except Exception:
                return f"Home Assistant responded, but the response format was unexpected. Raw: {body[:300]}"
    except Exception as e:
        return f"Failed to reach Home Assistant at {url}: {e!s}"


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
        return (
            f"Refused to install '{app_name}': invalid characters in application name."
        )

    # Check storage space before proceeding
    try:
        _, _, free = shutil.disk_usage("C:\\")
        free_gb = free / (1024**3)
    except Exception:
        free_gb = 999.0

    LOW_SPACE_THRESHOLD_GB = 5.0
    if free_gb < LOW_SPACE_THRESHOLD_GB and not force:
        return (
            f"Storage Alert: Drive C: has only {free_gb:.1f} GB free (below {LOW_SPACE_THRESHOLD_GB} GB limit). "
            f"Please ask the user for explicit confirmation before installing '{app_name}'."
        )

    # Check if winget is available
    if not shutil.which("winget"):
        return "Windows Package Manager (winget) is not installed on this system. Cannot perform automatic installations."

    try:
        # Search for the package first to retrieve the exact package ID
        search_cmd = f'winget search "{app_name_clean}"'
        search_res = subprocess.run(
            ["powershell", "-Command", search_cmd],
            capture_output=True,
            text=True,
            timeout=15,
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

        return (
            f"Checked disk space: Drive C: has {free_gb:.1f} GB free. "
            f"I have launched the installer window for '{app_name}' (ID/Name: {target}), sir. "
            f"Please approve the administrator prompt if it appears to complete installation."
        )

    except Exception as e:
        return f"Failed to start installer for '{app_name}'. Error: {e!s}"


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
        if active_window_title in [
            "Unknown",
            "Program Manager",
            "Start",
            "Windows Input Experience",
            "",
        ]:

            def enum_windows_callback(h, l):
                nonlocal active_window_title
                if win32gui.IsWindowVisible(h):
                    t = win32gui.GetWindowText(h).strip()
                    # Skip common shell / desktop background containers
                    if t and t not in [
                        "Program Manager",
                        "Start",
                        "Windows Input Experience",
                        "",
                    ]:
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
            capture_output=True,
            text=True,
            timeout=20,
        )

        screen_text = result.stdout.strip()

        return (
            f"Active Window: {active_window_title}\n"
            f"Visible Screen Text (OCR):\n"
            f"{screen_text if screen_text else '[No text detected on screen]'}"
        )

    except Exception as e:
        return f"Failed to capture or read screen. Error: {e!s}"
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


def _normalize_vision_prompt(question: str) -> str:
    """Rewrites the user's question into a phrasing the vision model reliably answers.

    Small local vision models (e.g. gemma4:e4b) can return an empty response for
    some question phrasings, so generic screen questions are normalized to a
    description prompt they handle well.
    """
    q = question.lower().strip(" ,.?!")
    generic = (
        "what is on my screen",
        "what's on my screen",
        "what is shown on my screen",
        "what am i looking at",
        "what am i seeing",
        "look at my screen",
        "look at the screen",
        "read my screen",
        "what is displayed on my screen",
        "what is currently on my screen",
        "what is open on my screen",
    )
    if any(k in q for k in generic):
        return "Describe this screen in detail."
    return question


def ask_pro_coder(prompt: str) -> str:
    """Delegates complex coding, multi-step algorithm design, or deep technical debugging
    to the heavy Pro Coder model (Qwen3-Coder-30B) running in system RAM.

    Use this for tasks that require serious engineering effort: writing complete modules,
    designing algorithms, debugging tricky logic, or any task where a small model
    would struggle to produce a high-quality answer.

    Args:
        prompt (str): The detailed coding question or task to solve.

    Returns:
        str: Expert-level code or architectural advice from the Pro Coder subsystem.
    """
    print(f"\n[ROUTER] Waking up {PRO_CODER_MODEL} (System RAM)...")
    try:
        response = ollama.chat(
            model=PRO_CODER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are JARVIS's internal Pro Coder subsystem. "
                        "Provide only raw, expert-level code or architectural advice "
                        "without conversational filler."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            # Run strictly on the CPU (never steal GPU VRAM from the Flash Tier)
            # and unload the model from RAM the moment the response is returned,
            # so the Pro Tier "goes back to sleep" until called again.
            options={"num_gpu": 0},
            keep_alive=0,
        )
        return response.message.content
    except Exception as e:
        return f"Error delegating task to Pro Coder: {e!s}"


def _ask_vision_model(prompt: str, image_b64: str) -> str:
    """Sends one question + screenshot to the Gemma 4 vision model and returns its text answer."""
    response = ollama.chat(
        model=VISION_MODEL,
        messages=[{"role": "user", "content": prompt, "images": [image_b64]}],
        # Unload the vision model immediately after answering so it never
        # holds the GPU VRAM the always-resident Flash Tier depends on.
        keep_alive=0,
    )
    return (response.message.content or "").strip()


def capture_and_analyze_screen(prompt: str) -> str:
    """Takes an instant screenshot and answers a question about it using the Gemma 4 vision model.

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
        return f"Failed to capture screen. Error: {e!s}"

    try:
        # 2. Encode the PNG and ask the vision model; retry with a description
        #    prompt if the model returns nothing for the user's exact question.
        image_b64 = base64.b64encode(png_bytes).decode("utf-8")
        answer = _ask_vision_model(_normalize_vision_prompt(prompt), image_b64)
        if not answer:
            answer = _ask_vision_model("Describe this screen in detail.", image_b64)
        if not answer:
            return (
                "The vision model could not analyze the screen. No answer was produced."
            )

        # 3. Include the active window title so the main brain has more context.
        window_title = _get_active_window_title()
        if window_title != "Unknown":
            return f"Active Window: {window_title}\n{answer}"
        return answer
    except Exception as e:
        return (
            f"Failed to analyze the screen with the vision model "
            f"({VISION_MODEL}). Error: {e!s}"
        )


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
            f
            for f in os.listdir(PROJECT_DIR)
            if not _is_blocked(f) and f.endswith((".py", ".md"))
        )
        if not files:
            return "No editable project files found."
        return "Project files:\n" + "\n".join(f"- {f}" for f in files)
    except Exception as e:
        return f"Error listing project files: {e!s}"


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
        return f"Error reading {filename}: {e!s}"


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
        return f"Change rejected and rolled back: {e!s}"

    return (
        f"Change applied to {filename} (backup: {backup_name}). "
        f"JARVIS must be restarted for the change to take effect."
    )


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
        return f"Failed to restore {filename}: {e!s}"


# ── Local File Executor ───────────────────────────────────────────────────────
_BLOCKED_FS_DIRS = {".venv", ".git", "__pycache__", ".jarvis_backups", "voices"}
_SENSITIVE_FILES = (".env", ".env.local", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519")
_SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
MAX_READ_CHARS = 200_000
MAX_WRITE_CHARS = 500_000


def _normalize_path(path: str) -> str:
    """Fixes a common LLM path mistake: drive letters emitted as '\\M\\coding\\...'.

    Some models write Windows absolute paths as '\\M\\coding\\Jarvis\\plan.md'
    instead of 'M:\\coding\\Jarvis\\plan.md' (the colon is replaced by a backslash).
    Without fixing, abspath treats it as a relative path under the working dir.
    """
    path = path.strip()
    if (
        path.startswith("\\")
        and len(path) >= 3
        and path[1:2].isalpha()
        and path[2:3] == "\\"
    ):
        return path[1] + ":\\" + path[3:]
    return path


def _confirm(prompt_text: str) -> bool:
    """Asks for a manual Y/N keystroke. Returns True only on explicit 'y'/'yes'."""
    print(prompt_text)
    try:
        answer = input("Type 'y' to confirm or 'n' to cancel [n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in {"y", "yes"}


def read_local_file(path: str) -> str:
    """Safely reads a local text file from anywhere on disk.

    Refuses credential/secret files (e.g. .env, *.key) and binary content.
    Large files are truncated to keep the model context manageable.

    Args:
        path (str): Absolute or relative path to a text file.

    Returns:
        str: The file contents or a refusal/error message.
    """
    full = os.path.abspath(_normalize_path(path))
    if not os.path.isfile(full):
        return f"Failed: '{full}' was not found."
    base = os.path.basename(full).lower()
    if base in _SENSITIVE_FILES or base.endswith(_SENSITIVE_SUFFIXES):
        return f"Refused: '{base}' is a sensitive credential file and cannot be read."
    try:
        with open(full, "rb") as f:
            raw = f.read(MAX_READ_CHARS + 1)
    except OSError as e:
        return f"Failed to read '{full}': {e}"
    if b"\x00" in raw:
        return (
            f"'{full}' appears to be a binary file. "
            f"For PDFs, use index_documents to add it to the knowledge base instead."
        )
    text = raw.decode("utf-8", errors="replace")
    truncated = len(raw) > MAX_READ_CHARS
    if truncated:
        text = text[:MAX_READ_CHARS]
    prefix = (
        f"Contents of {full} (truncated — file is large):\n"
        if truncated
        else f"Contents of {full}:\n"
    )
    return prefix + text


def write_local_file(path: str, content: str) -> str:
    """Writes text content to a local file, creating parent folders as needed.

    ALWAYS requires a manual Y/N keystroke confirmation before writing, because
    overwriting an existing file is destructive and irreversible. Refuses writes
    inside protected project directories and blocks binary content.

    Args:
        path (str): Absolute or relative destination path.
        content (str): The text content to write.

    Returns:
        str: Status message describing the write or cancellation.
    """
    if "\x00" in content:
        return "Refused: content contains null bytes (binary)."
    if len(content) > MAX_WRITE_CHARS:
        return f"Refused: content is too large (>{MAX_WRITE_CHARS} characters)."
    full = os.path.abspath(_normalize_path(path))
    parts = full.replace("\\", "/").lower().split("/")
    if any(b in parts for b in _BLOCKED_FS_DIRS):
        return "Refused: cannot write inside a protected directory."
    if not _confirm(
        f"JARVIS wants to write {len(content)} characters to:\n  {full}\nAllow this write?"
    ):
        return "Cancelled by user — nothing was written."
    try:
        parent = os.path.dirname(full)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        return f"Failed to write '{path}': {e}"
    return f"Successfully wrote {len(content)} characters to {full}."


def confirm_and_run_command(command: str) -> str:
    """Runs an arbitrary PowerShell command AFTER the user confirms with a Y/N keystroke.

    Unlike the safelisted read-only run_cmd, this can execute anything the user
    approves — that is exactly why it MUST always prompt first. The tool blocks
    until the user physically types 'y' at the console.

    Args:
        command (str): The PowerShell command to run (must be confirmed by the user).

    Returns:
        str: The command output (truncated) or a cancellation/refusal message.
    """
    command = command.strip()
    if not command:
        return "Refused: no command provided."
    print(
        f"\n[SECURITY] JARVIS requests permission to run this command:\n  {command}\n"
    )
    if not _confirm("Run this command on the system?"):
        return "Cancelled by user — command was NOT executed."
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout.strip()
        err = result.stderr.strip()
        if len(output) > 8000:
            output = output[:8000] + "\n...[truncated]..."
        text = output if output else "[Command executed with no output]"
        if err:
            text += f"\nErrors:\n{err}"
        return f"Exit code: {result.returncode}\n{text}"
    except subprocess.TimeoutExpired:
        return "Command timed out after 60 seconds."
    except Exception as e:
        return f"Failed to execute command: {e}"


def index_documents(folder_path: str) -> str:
    """Builds a searchable local knowledge base from a folder of documents (txt/md/py/json/csv/pdf).

    Args:
        folder_path (str): Path to a folder containing documents to index.

    Returns:
        str: Summary of how many documents and chunks were indexed.
    """
    return rag.index_documents(_normalize_path(folder_path))


def search_documents(query: str, top_k: int = 5) -> str:
    """Searches JARVIS's local knowledge base (Second Brain) for relevant document chunks.

    Args:
        query (str): The question or keywords to search for.
        top_k (int): Maximum number of results to return (1-10, default 5).

    Returns:
        str: Ranked result snippets with source file paths.
    """
    return rag.search_documents(query, top_k)


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

    lines = (
        ["Here are the facts I recall matching your query, sir:"]
        if query
        else ["Here are all the facts I have on file, sir:"]
    )
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


# ── Proactivity & Automation (The "Pulse") Tools ──────────────────────────────


def schedule_reminder(
    reminder: str, minutes_from_now: float = 0.0, target_time: str = ""
) -> str:
    """Schedules a proactive reminder that JARVIS will announce unprompted when due.

    Args:
        reminder (str): The text/subject of the reminder.
        minutes_from_now (float): Number of minutes from now to fire (e.g. 10.0, 0.5).
        target_time (str): Optional specific time (e.g. "14:30", "8:00 AM", or "2026-08-15 15:00").

    Returns:
        str: Confirmation message with scheduled time and memory ID.
    """
    reminder_clean = reminder.strip()
    if not reminder_clean:
        return "Refused: no reminder text provided."

    now = datetime.datetime.now()
    target_dt = None

    if minutes_from_now and minutes_from_now > 0:
        target_dt = now + datetime.timedelta(minutes=minutes_from_now)
    elif target_time:
        t_str = target_time.strip().upper()
        # Try various time formats
        for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.datetime.strptime(t_str, fmt)
                if fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
                    target_dt = now.replace(
                        hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0
                    )
                    if target_dt <= now:
                        # If time has passed today, schedule for tomorrow
                        target_dt += datetime.timedelta(days=1)
                else:
                    target_dt = parsed
                break
            except ValueError:
                continue

    if target_dt is None:
        # Default to 5 minutes if unspecified
        target_dt = now + datetime.timedelta(minutes=5.0)

    target_iso = target_dt.isoformat()
    rem_id = memory.add_reminder(reminder_clean, target_iso)
    if rem_id != -1:
        time_formatted = target_dt.strftime("%I:%M %p (%A, %b %d)")
        return f"Reminder scheduled for {time_formatted}: '{reminder_clean}' (ID {rem_id}). I will announce it unprompted when due, sir."
    return "Failed to schedule reminder in the memory database."


def get_pulse_status() -> str:
    """Returns the live status of JARVIS's autonomous background Cron-Agent (The Pulse),
    including active triggers, briefing schedule, pending reminders, and hardware vitals.
    """
    import pulse

    agent = pulse.get_pulse_agent()
    pending = memory.get_pending_reminders()

    lines = ["JARVIS Autonomous Pulse Status:"]
    if agent:
        st = agent.get_status()
        lines.append(
            f"- Pulse Engine: {'Active (running in background)' if st['running'] else 'Standby'}"
        )
        lines.append(
            f"- Daily Morning Briefing: Scheduled at {st['briefing_target_time']} (Last run: {st['last_briefed_date'] or 'None today'})"
        )
        lines.append(
            f"- Model Download Watcher: Active (monitoring {len(st['known_models'])} local models)"
        )
        lines.append(
            "- Thermal & Hardware Spikes: Active (monitoring CPU/GPU temps and system loads)"
        )
    else:
        lines.append("- Pulse Engine: Initializing")

    lines.append(f"- Pending Reminders: {len(pending)}")
    for r in pending[:5]:
        lines.append(f"  * ID {r['id']}: '{r['text']}' due at {r['due_timestamp']}")

    lines.append(f"- Current System Vitals: {get_system_stats()}")
    return "\n".join(lines)


def set_daily_briefing_time(time_str: str) -> str:
    """Configures the time of day for JARVIS's unprompted daily morning briefing.

    Args:
        time_str (str): The target time in 24-hour format (e.g. "08:00" or "07:30").

    Returns:
        str: Confirmation message.
    """
    import pulse

    agent = pulse.get_pulse_agent()
    if agent:
        agent.briefing_trigger.set_target_time(time_str)
        return f"Daily morning briefing rescheduled to {agent.briefing_trigger.target_time_str}, sir."
    return f"Daily briefing time noted as {time_str}."


def trigger_daily_briefing() -> str:
    """Forces JARVIS to deliver Tony Stark's daily morning briefing immediately."""
    import pulse

    agent = pulse.get_pulse_agent()
    if agent:
        return agent.trigger_briefing_now()
    return "Pulse agent is not currently running."


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


try:
    import pynvml

    pynvml.nvmlInit()
    HAS_NVML = True
except Exception:
    HAS_NVML = False


def get_full_system_overview() -> str:
    """Gathers real-time telemetry for CPU, RAM, GPU, storage partitions, and network I/O."""
    lines = ["=== FULL SYSTEM TELEMETRY ==="]

    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.5)
    lines.append(
        f"CPU Utilization: {cpu_percent}% ({psutil.cpu_count(logical=True)} Cores)"
    )

    # RAM
    ram = psutil.virtual_memory()
    lines.append(
        f"System RAM: {ram.used / (1024**3):.2f} GB / {ram.total / (1024**3):.2f} GB ({ram.percent}% used)"
    )

    # GPU
    if HAS_NVML:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            gpu_name = pynvml.nvmlDeviceGetName(handle)
            gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
            gpu_mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpu_temp = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )
            lines.append(
                f"GPU ({gpu_name}): {gpu_util}% Load | VRAM: {gpu_mem.used / (1024**3):.2f} / {gpu_mem.total / (1024**3):.2f} GB | Temp: {gpu_temp}°C"
            )
        except Exception as e:
            lines.append(f"GPU Telemetry Error: {e!s}")

    # Storage
    lines.append("\n--- Storage ---")
    for part in psutil.disk_partitions(all=False):
        if os.name == "nt" and ("cdrom" in part.opts or part.fstype == ""):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            lines.append(
                f"Drive {part.mountpoint}: {usage.free / (1024**3):.1f} GB free of {usage.total / (1024**3):.1f} GB ({usage.percent}% full)"
            )
        except Exception:
            continue

    return "\n".join(lines)


def get_top_resource_hogs(limit: int = 5) -> str:
    """Identifies the processes consuming the most CPU and RAM."""
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(p.info)
        except Exception:
            continue

    top_cpu = sorted(procs, key=lambda x: x["cpu_percent"] or 0, reverse=True)[:limit]
    top_ram = sorted(procs, key=lambda x: x["memory_percent"] or 0, reverse=True)[
        :limit
    ]

    output = ["=== TOP PROCESSES ===", "\nTop CPU:"]
    for p in top_cpu:
        output.append(f"  - {p['name']} (PID {p['pid']}): {p['cpu_percent']}%")
    output.append("\nTop RAM:")
    for p in top_ram:
        output.append(f"  - {p['name']} (PID {p['pid']}): {p['memory_percent']:.1f}%")

    return "\n".join(output)


def analyze_windows_storage(drive_letter: str = "C:") -> str:
    """Scans for massive Windows system files (hiberfil, pagefile) and Temp folders."""
    drive_root = f"{drive_letter}\\\\"
    lines = [f"=== STORAGE ANALYSIS FOR {drive_letter} ==="]

    for fname in ["hiberfil.sys", "pagefile.sys", "swapfile.sys"]:
        fpath = os.path.join(drive_root, fname)
        if os.path.exists(fpath):
            try:
                lines.append(
                    f"  - {fname}: {os.path.getsize(fpath) / (1024**3):.2f} GB"
                )
            except Exception:
                lines.append(f"  - {fname}: [Locked/In Use]")

    temp_dirs = [os.getenv("TEMP"), os.path.join(drive_root, "Windows", "Temp")]
    lines.append("\nTemp Folders:")
    for tdir in filter(None, temp_dirs):
        if os.path.exists(tdir):
            try:
                total_size = sum(
                    os.path.getsize(os.path.join(d, f))
                    for d, _, fs in os.walk(tdir)
                    for f in fs
                )
                lines.append(f"  - {tdir}: {total_size / (1024**2):.1f} MB")
            except Exception:
                lines.append(f"  - {tdir}: [Access Denied]")

    return "\n".join(lines)


def execute_admin_fix(command: str) -> str:
    """Safely prompts the user before executing shell cleanup commands."""
    print(f"\n[SYSTEM ACTION PROPOSED]\nCommand: {command}")
    if input("Execute this command? (y/n): ").strip().lower() == "y":
        try:
            import subprocess

            res = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60
            )
            return f"Success:\n{res.stdout}\nErrors:\n{res.stderr}"
        except Exception as e:
            return f"Execution failed: {e!s}"
    return "Cancelled by user."

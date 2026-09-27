"""Launcher for the JARVIS Cyberpunk Desktop HUD GUI.

Starts the local GUI server and opens the interface in a dedicated,
borderless desktop application window (via Edge/Chrome app-mode).
"""

import os
import shutil
import subprocess
import sys
import time
import webbrowser

import gui_server
import pulse


def find_browser_app_runner() -> tuple[str, list[str]]:
    """Locates Edge or Chrome to run in standalone desktop App Mode."""
    url = "http://127.0.0.1:8765"
    app_flag = f"--app={url}"
    size_flag = "--window-size=1160,840"

    candidates = [
        # Edge candidates
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("msedge.exe") or "",
        shutil.which("msedge") or "",
        # Chrome candidates
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        shutil.which("chrome.exe") or "",
        shutil.which("chrome") or "",
    ]

    for path in candidates:
        if path and os.path.isfile(path):
            return path, [path, app_flag, size_flag]

    return "", []


def launch_gui(port: int = 8765) -> None:
    """Starts the GUI server and desktop application window."""
    print("=======================================================")
    print("          INITIALIZING JARVIS CYBERPUNK HUD            ")
    print(f"      Server running at: http://127.0.0.1:{port}       ")
    print("=======================================================")

    # 1. Start the GUI server daemon
    srv = gui_server.run_server(port)

    # 2. Start the Pulse background cron daemon
    try:
        def _on_pulse_speak(announcement_text: str):
            print(f"\n[Pulse Announcement] {announcement_text}")

        pulse_engine = pulse.init_pulse_agent(
            on_speak=_on_pulse_speak,
            history_ref=[],
            is_text_mode=True,
        )
        pulse_engine.start()
    except Exception as e:
        print(f"[Pulse Notice] {e}")

    # 3. Launch dedicated desktop app window
    exe_path, args = find_browser_app_runner()

    if exe_path and args:
        print(f"Launching standalone Desktop HUD window via: {os.path.basename(exe_path)}")
        try:
            proc = subprocess.Popen(args)
        except Exception as e:
            print(f"Could not launch app mode ({e}), falling back to default browser.")
            webbrowser.open(f"http://127.0.0.1:{port}")
            proc = None
    else:
        print("Opening in default web browser...")
        webbrowser.open(f"http://127.0.0.1:{port}")
        proc = None

    print("\nJARVIS Desktop HUD is active. Press Ctrl+C in this terminal to shut down.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down JARVIS HUD...")

    finally:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        srv.shutdown()
        print("JARVIS HUD stopped.")


if __name__ == "__main__":
    launch_gui()

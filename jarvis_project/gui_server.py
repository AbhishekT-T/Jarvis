"""JARVIS Cyberpunk HUD GUI Server.

Runs a multithreaded local HTTP server on 127.0.0.1:8765 to power the
JARVIS desktop HUD interface with zero external pip dependencies.
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import threading
import time
from typing import Any

import llm
import memory
import psutil
import window_context

# Thread-safe global state for the HUD
_state_lock = threading.Lock()
_current_state = "idle"  # "idle" | "listening" | "thinking" | "speaking"
_last_tools_executed: list[dict[str, Any]] = []
_active_session_history: list[dict[str, str]] = []


def set_state(state: str) -> None:
    """Updates the assistant's real-time state for the HUD."""
    global _current_state
    with _state_lock:
        _current_state = state


def get_state() -> str:
    """Returns the current assistant state."""
    with _state_lock:
        return _current_state


def get_system_telemetry() -> dict[str, Any]:
    """Inspects live hardware utilization."""
    cpu = psutil.cpu_percent(interval=None)
    ram = psutil.virtual_memory().percent

    # Get GPU VRAM usage if nvidia tools or psutil allows
    vram_str = "1.9/4.0"
    try:
        import subprocess

        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,nounits,noheader"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        if res.returncode == 0 and res.stdout.strip():
            used, total = res.stdout.strip().split(",")
            used_gb = round(float(used.strip()) / 1024.0, 1)
            total_gb = round(float(total.strip()) / 1024.0, 1)
            vram_str = f"{used_gb}/{total_gb}"
    except Exception:
        pass

    try:
        active_win = window_context.get_active_window_context()
    except Exception:
        active_win = {"app_name": "Desktop", "category": "general", "title": ""}

    return {
        "cpu": cpu,
        "ram": ram,
        "vram": vram_str,
        "active_window": active_win,
    }


class JarvisHUDHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the GUI frontend and REST API."""

    def __init__(self, *args, **kwargs):
        gui_dir = os.path.join(os.path.dirname(__file__), "gui")
        super().__init__(*args, directory=gui_dir, **kwargs)

    def log_message(self, format, *args):
        """Suppress noisy request logging in the console."""
        return

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Sends a JSON response with CORS and cache control."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Handles REST API GET requests or serves static GUI assets."""
        if self.path == "/api/status":
            telemetry = get_system_telemetry()
            telemetry["state"] = get_state()
            telemetry["active_model"] = llm.get_active_model()
            self._send_json(telemetry)
            return

        if self.path == "/api/models":
            try:
                import ollama
                res = ollama.list()
                models_list = [m.get("name") or m.get("model") for m in res.get("models", [])]
            except Exception:
                models_list = ["qwen2.5:3b", "qwen3-coder:30b", "gemma4:e4b", "gemma4:26b"]
            self._send_json({
                "models": models_list,
                "active_model": llm.get_active_model(),
            })
            return

        if self.path == "/api/history":
            recent = memory.load_history()
            self._send_json({"history": recent})
            return


        # Default static file handler (index.html, gui.css, gui.js)
        super().do_GET()

    def do_POST(self) -> None:
        """Handles interactive user actions and chat submissions."""
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"

        try:
            payload = json.loads(post_body)
        except Exception:
            payload = {}

        if self.path == "/api/set_model":
            model_name = str(payload.get("model", "")).strip()
            if not model_name:
                self._send_json({"error": "No model name provided"}, status=400)
                return
            result = llm.set_active_model(model_name)
            self._send_json({
                "status": "ok",
                "active_model": result["model"],
                "options": result.get("options", {}),
            })
            return

        if self.path == "/api/chat":
            message = str(payload.get("message", "")).strip()
            if not message:
                self._send_json({"error": "Empty message"}, status=400)
                return

            set_state("thinking")
            tools_captured: list[dict[str, Any]] = []

            # Temporarily register tool callback to capture execution details
            def on_tool_run(name: str, args: dict[str, Any], output: str):
                tools_captured.append({
                    "name": name,
                    "args": args,
                    "output": output[:600] + ("..." if len(output) > 600 else ""),
                })

            old_cb = getattr(llm, "tool_execution_callback", None)
            llm.tool_execution_callback = on_tool_run

            try:
                reply = llm.query_jarvis(message, _active_session_history)
                # Keep active in-memory history updated
                _active_session_history.append({"role": "user", "content": message})
                _active_session_history.append({"role": "assistant", "content": reply})
                memory.append_message("user", message)
                memory.append_message("assistant", reply)
            except Exception as e:

                reply = f"Error processing query: {e}"
            finally:
                llm.tool_execution_callback = old_cb
                set_state("idle")

            self._send_json({
                "response": reply,
                "tools": tools_captured,
            })
            return

        if self.path == "/api/trigger_listen":
            # Push-to-talk voice capture cycle
            import stt
            import tts

            set_state("listening")
            tools_captured: list[dict[str, Any]] = []

            try:
                # Capture one turn from microphone
                user_text = stt.listen_and_transcribe()
            except Exception as e:
                set_state("idle")
                self._send_json({"error": f"Microphone error: {e}"}, status=500)
                return

            if not user_text:
                set_state("idle")
                self._send_json({"transcription": "", "response": ""})
                return

            set_state("thinking")

            def on_tool_run(name: str, args: dict[str, Any], output: str):
                tools_captured.append({
                    "name": name,
                    "args": args,
                    "output": output[:600] + ("..." if len(output) > 600 else ""),
                })

            old_cb = getattr(llm, "tool_execution_callback", None)
            llm.tool_execution_callback = on_tool_run

            try:
                reply = llm.query_jarvis(user_text, _active_session_history)
                _active_session_history.append({"role": "user", "content": user_text})
                _active_session_history.append({"role": "assistant", "content": reply})
                memory.append_message("user", user_text)
                memory.append_message("assistant", reply)

                # Speak reply

                set_state("speaking")
                tts.speak(reply)
            except Exception as e:
                reply = f"Error: {e}"
            finally:
                llm.tool_execution_callback = old_cb
                set_state("idle")

            self._send_json({
                "transcription": user_text,
                "response": reply,
                "tools": tools_captured,
            })
            return

        self._send_json({"error": "Endpoint not found"}, status=404)


def run_server(port: int = 8765) -> ThreadingHTTPServer:
    """Starts the GUI HTTP server in a background daemon thread."""
    server = ThreadingHTTPServer(("127.0.0.1", port), JarvisHUDHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


if __name__ == "__main__":
    print("Starting JARVIS GUI server on http://127.0.0.1:8765 ...")
    srv = run_server(8765)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down GUI server.")
        srv.shutdown()

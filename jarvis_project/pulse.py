import datetime
import os
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable

import memory
import ollama
import psutil
import tools

# ── Model Tier Configuration ──────────────────────────────────────────────────
# Flash Tier is locked into GPU VRAM and kept resident for zero latency.
FLASH_MODEL = "qwen2.5:3b"
FLASH_OPTIONS = {"num_gpu": -1}
FLASH_KEEP_ALIVE = -1

PULSE_STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".pulse_state.json"
)


class TurnCoordinator:
    """Thread-safe coordinator that prevents background unprompted speech
    from colliding with the active user conversation turn or audio playback.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._is_user_interacting = False

    def start_user_interaction(self) -> None:
        with self._lock:
            self._is_user_interacting = True

    def end_user_interaction(self) -> None:
        with self._lock:
            self._is_user_interacting = False

    def is_busy(self) -> bool:
        with self._lock:
            return self._is_user_interacting

    def acquire_pulse_turn(self, timeout_sec: float = 30.0) -> bool:
        """Waits until user interaction is idle, then returns True."""
        start = time.time()
        while time.time() - start < timeout_sec:
            with self._lock:
                if not self._is_user_interacting:
                    return True
            time.sleep(0.5)
        return False


# Global coordinator instance
coordinator = TurnCoordinator()


def generate_unprompted_speech(event_type: str, event_context: str) -> str:
    """Uses the Flash Tier (qwen2.5:3b) to generate a stylish, persona-rich
    spoken announcement for an unprompted background event.
    """
    system_prompt = (
        "You are JARVIS, Tony Stark's personal AI assistant running locally. "
        "You are speaking unprompted to Tony Stark (sir) to deliver an important proactive alert, "
        "notification, or scheduled briefing.\n"
        "Persona & Guidelines:\n"
        "- Speak in character: sharp, composed, courteous, and natural, with understated wit.\n"
        "- Keep sentences short and spoken. Never output bullet points, code blocks, or markdown lists.\n"
        "- For alerts or download completions, deliver 1 to 2 concise sentences.\n"
        "- For morning briefings, deliver a cohesive 2 to 3 sentence spoken summary covering the day, weather, and systems.\n"
        "- Address the user as 'sir' where appropriate."
    )

    user_prompt = (
        f"Deliver the following proactive event announcement to sir:\n"
        f"Event Type: {event_type}\n"
        f"Event Data & Context:\n{event_context}\n\n"
        f"Speak your announcement now:"
    )

    try:
        response = ollama.chat(
            model=FLASH_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options=FLASH_OPTIONS,
            keep_alive=FLASH_KEEP_ALIVE,
        )
        content = (response.message.content or "").strip()
        if content:
            return content
    except Exception as e:
        print(f"[PULSE LLM ERROR] {e}")

    # Fallback phrasing if model call fails
    if "download" in event_type.lower():
        return f"Sir, background notification: {event_context}."
    if "briefing" in event_type.lower():
        return f"Good morning, sir. Daily briefing: {event_context}."
    if "spike" in event_type.lower() or "hardware" in event_type.lower():
        return f"System alert, sir. {event_context}."
    if "reminder" in event_type.lower():
        return f"Sir, reminding you: {event_context}."
    return f"Sir, {event_context}."


# ── Triggers ──────────────────────────────────────────────────────────────────


class BaseTrigger:
    """Base class for all Pulse background event triggers."""

    def __init__(
        self, name: str, check_interval_sec: float = 30.0, cooldown_sec: float = 300.0
    ):
        self.name = name
        self.check_interval_sec = check_interval_sec
        self.cooldown_sec = cooldown_sec
        self.last_checked = 0.0
        self.last_fired = 0.0

    def can_check(self, now: float) -> bool:
        return (now - self.last_checked) >= self.check_interval_sec

    def in_cooldown(self, now: float) -> bool:
        return (now - self.last_fired) < self.cooldown_sec

    def evaluate(self, now: float) -> tuple[bool, str, str]:
        """Evaluates condition. Returns (should_fire, event_type, event_context)."""
        raise NotImplementedError


class ModelDownloadTrigger(BaseTrigger):
    """Watches for the completion of large Ollama model downloads in the background."""

    def __init__(self):
        super().__init__(
            name="ModelDownloadTrigger", check_interval_sec=15.0, cooldown_sec=10.0
        )
        self.known_models: set[str] = set()
        self.announced_models: set[str] = set()
        self._initialized = False

    def _init_models(self) -> None:
        try:
            res = ollama.list()
            self.known_models = {m.model for m in res.models}
            # Treat existing models as already known so we don't announce on startup
            self.announced_models = set(self.known_models)
            self._initialized = True
        except Exception:
            pass

    def evaluate(self, now: float) -> tuple[bool, str, str]:
        self.last_checked = now
        if not self._initialized:
            self._init_models()
            return False, "", ""

        try:
            res = ollama.list()
            current_models = {m.model for m in res.models}
            new_models = current_models - self.announced_models

            if new_models:
                # Found newly downloaded model(s)
                model_name = sorted(list(new_models))[0]
                self.announced_models.add(model_name)
                self.known_models.add(model_name)
                self.last_fired = now

                tier_desc = "general model"
                if "qwen3-coder" in model_name or "coder" in model_name:
                    tier_desc = "Pro Tier heavy programming subsystem (Qwen3-Coder)"
                elif "gemma4" in model_name or "vision" in model_name:
                    tier_desc = "Vision Tier desktop screen analyzer (Gemma 4)"
                elif "nomic-embed" in model_name:
                    tier_desc = "Second Brain document embedding engine"

                event_type = "Model Download Complete"
                event_context = (
                    f"The background model download for '{model_name}' has successfully finished. "
                    f"This model powers the {tier_desc} and is now fully available locally on this machine."
                )
                return True, event_type, event_context

        except Exception:
            pass

        return False, "", ""


class HardwareSpikeTrigger(BaseTrigger):
    """Monitors CPU temperature, GPU temperature, CPU utilization, RAM utilization,
    and low disk space. Fires unprompted warnings when safety thresholds are breached.
    """

    def __init__(self):
        super().__init__(
            name="HardwareSpikeTrigger", check_interval_sec=30.0, cooldown_sec=600.0
        )
        self.last_alert_type = ""
        self.consecutive_cpu_spikes = 0

    def _get_gpu_temp(self) -> int | None:
        if shutil.which("nvidia-smi"):
            try:
                res = subprocess.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=temperature.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                val = res.stdout.strip()
                if val.isdigit():
                    return int(val)
            except Exception:
                pass
        return None

    def _get_cpu_temp(self) -> float | None:
        # 1. Try psutil sensors
        try:
            temps = (
                psutil.sensors_temperatures()
                if hasattr(psutil, "sensors_temperatures")
                else None
            )
            if temps:
                for _, entries in temps.items():
                    for entry in entries:
                        if entry.current and entry.current > 0:
                            return entry.current
        except Exception:
            pass
        return None

    def evaluate(self, now: float) -> tuple[bool, str, str]:
        self.last_checked = now

        # 1. Check GPU / CPU Temperature
        gpu_temp = self._get_gpu_temp()
        cpu_temp = self._get_cpu_temp()

        if gpu_temp is not None and gpu_temp >= 83:
            if not self.in_cooldown(now) or self.last_alert_type != "gpu_temp":
                self.last_fired = now
                self.last_alert_type = "gpu_temp"
                event_type = "Hardware Thermal Spike"
                event_context = (
                    f"GPU temperature has spiked to {gpu_temp}°C (threshold 83°C). "
                    f"Recommend inspecting active graphics/compute workloads."
                )
                return True, event_type, event_context

        if cpu_temp is not None and cpu_temp >= 85:
            if not self.in_cooldown(now) or self.last_alert_type != "cpu_temp":
                self.last_fired = now
                self.last_alert_type = "cpu_temp"
                event_type = "Hardware Thermal Spike"
                event_context = (
                    f"CPU temperature has spiked to {cpu_temp:.0f}°C (threshold 85°C). "
                    f"Recommend checking cooling or intensive tasks."
                )
                return True, event_type, event_context

        # 2. Check CPU utilization (sustained > 92%)
        cpu_usage = psutil.cpu_percent(interval=1.0)
        if cpu_usage >= 92.0:
            self.consecutive_cpu_spikes += 1
        else:
            self.consecutive_cpu_spikes = 0

        if self.consecutive_cpu_spikes >= 2:
            if not self.in_cooldown(now) or self.last_alert_type != "cpu_load":
                self.last_fired = now
                self.last_alert_type = "cpu_load"
                self.consecutive_cpu_spikes = 0
                top_procs = (
                    tools.get_top_consumers(3)
                    if hasattr(tools, "get_top_consumers")
                    else ""
                )
                event_type = "CPU Utilization Spike"
                event_context = (
                    f"CPU utilization has sustained at {cpu_usage:.0f}%. "
                    f"Top consuming processes:\n{top_procs}"
                )
                return True, event_type, event_context

        # 3. Check RAM utilization (> 92%)
        ram_usage = psutil.virtual_memory().percent
        if ram_usage >= 92.0:
            if not self.in_cooldown(now) or self.last_alert_type != "ram_load":
                self.last_fired = now
                self.last_alert_type = "ram_load"
                top_procs = (
                    tools.get_top_consumers(3)
                    if hasattr(tools, "get_top_consumers")
                    else ""
                )
                event_type = "Memory Pressure Alert"
                event_context = (
                    f"System RAM utilization is critically high at {ram_usage:.0f}%. "
                    f"Top processes:\n{top_procs}"
                )
                return True, event_type, event_context

        # 4. Check Disk Space (< 5.0 GB)
        try:
            _, _, free = shutil.disk_usage("C:\\")
            free_gb = free / (1024**3)
            if free_gb < 5.0:
                if not self.in_cooldown(now) or self.last_alert_type != "disk_space":
                    self.last_fired = now
                    self.last_alert_type = "disk_space"
                    event_type = "Storage Space Warning"
                    event_context = f"Drive C: is critically low on space with only {free_gb:.1f} GB remaining."
                    return True, event_type, event_context
        except Exception:
            pass

        return False, "", ""


class DailyBriefingTrigger(BaseTrigger):
    """Schedules and reads a daily morning briefing at 8:00 AM (or user-configured time)."""

    def __init__(self, target_time_str: str = "08:00"):
        super().__init__(
            name="DailyBriefingTrigger", check_interval_sec=20.0, cooldown_sec=3600.0
        )
        self.target_time_str = target_time_str  # "HH:MM" 24-hour format
        self.last_briefed_date: str | None = None

    def set_target_time(self, time_str: str) -> None:
        # Validate format HH:MM
        if re.match(r"^\d{1,2}:\d{2}$", time_str.strip()):
            parts = time_str.strip().split(":")
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                self.target_time_str = f"{h:02d}:{m:02d}"

    def evaluate(self, now: float) -> tuple[bool, str, str]:
        self.last_checked = now
        now_dt = datetime.datetime.now()
        today_str = now_dt.strftime("%Y-%m-%d")

        # Parse target hour and minute
        try:
            th, tm = map(int, self.target_time_str.split(":"))
        except Exception:
            th, tm = 8, 0

        # Target datetime for today
        target_dt = now_dt.replace(hour=th, minute=tm, second=0, microsecond=0)

        # Fire if current time >= target time, we haven't briefed today yet, and it's within a 2-hour window
        if now_dt >= target_dt and (now_dt - target_dt).total_seconds() < 7200:
            if self.last_briefed_date != today_str:
                self.last_briefed_date = today_str
                self.last_fired = now

                # Gather live contextual data for the briefing
                date_str = now_dt.strftime("%A, %B %d, %Y at %I:%M %p")

                # Fetch weather
                weather_info = "Weather currently unavailable"
                try:
                    weather_info = tools.get_weather("New York")
                except Exception:
                    pass

                # Fetch system stats
                sys_stats = tools.get_system_stats()

                event_type = "Daily 8:00 AM Morning Briefing"
                event_context = (
                    f"Target Time: {self.target_time_str}\n"
                    f"Current Date & Time: {date_str}\n"
                    f"Live Weather: {weather_info}\n"
                    f"System Hardware Status: {sys_stats}\n"
                    f"Deliver a crisp, inspiring morning briefing to Tony Stark."
                )
                return True, event_type, event_context

        return False, "", ""


class ReminderTrigger(BaseTrigger):
    """Checks for pending scheduled reminders in SQLite and fires when due."""

    def __init__(self):
        super().__init__(
            name="ReminderTrigger", check_interval_sec=5.0, cooldown_sec=1.0
        )

    def evaluate(self, now: float) -> tuple[bool, str, str]:
        self.last_checked = now
        try:
            pending = memory.get_pending_reminders()
            if not pending:
                return False, "", ""

            now_iso = datetime.datetime.now().isoformat()
            for r in pending:
                due = r.get("due_timestamp", "")
                if due and due <= now_iso:
                    # Mark completed immediately
                    rem_id = r["id"]
                    rem_text = r["text"]
                    memory.mark_reminder_completed(rem_id)
                    self.last_fired = now

                    event_type = "Scheduled Reminder Due"
                    event_context = (
                        f"The user previously requested a reminder: '{rem_text}'. "
                        f"It is now due."
                    )
                    return True, event_type, event_context
        except Exception:
            pass

        return False, "", ""


# ── The Pulse Background Engine ───────────────────────────────────────────────


class PulseEngine:
    """The Autonomous Background Cron-Agent (The "Pulse").
    Runs in a secondary daemon thread, silently checking triggers, and initiating
    unprompted Flash Tier spoken announcements when conditions are met.
    """

    def __init__(
        self,
        on_speak: Callable[[str], None] | None = None,
        history_ref: list | None = None,
        is_text_mode: bool = False,
    ):
        self.on_speak = on_speak
        self.history_ref = history_ref if history_ref is not None else []
        self.is_text_mode = is_text_mode
        self._running = False
        self._thread: threading.Thread | None = None

        # Triggers registered in the Pulse engine
        self.model_trigger = ModelDownloadTrigger()
        self.hardware_trigger = HardwareSpikeTrigger()
        self.briefing_trigger = DailyBriefingTrigger(target_time_str="08:00")
        self.reminder_trigger = ReminderTrigger()

        self.triggers: list[BaseTrigger] = [
            self.model_trigger,
            self.hardware_trigger,
            self.briefing_trigger,
            self.reminder_trigger,
        ]

    def set_history_ref(self, history: list) -> None:
        self.history_ref = history

    def start(self) -> None:
        """Starts the background pulse loop in a daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="JarvisPulseThread"
        )
        self._thread.start()
        print("[PULSE] Background autonomous Cron-Agent initialized.")

    def stop(self) -> None:
        """Signals the background pulse loop to terminate."""
        self._running = False

    def trigger_briefing_now(self) -> str:
        """Forces an immediate test run of the daily briefing."""
        now = time.time()
        now_dt = datetime.datetime.now()
        date_str = now_dt.strftime("%A, %B %d, %Y at %I:%M %p")
        weather_info = tools.get_weather("New York")
        sys_stats = tools.get_system_stats()

        event_type = "Daily Morning Briefing (Manual Trigger)"
        event_context = (
            f"Current Date & Time: {date_str}\n"
            f"Live Weather: {weather_info}\n"
            f"System Hardware Status: {sys_stats}\n"
            f"Deliver a crisp morning briefing to Tony Stark."
        )
        return self._dispatch_event(event_type, event_context)

    def _dispatch_event(self, event_type: str, event_context: str) -> str:
        """Generates Flash Tier speech, speaks it, and logs to memory."""
        # Wait if user is currently interacting
        coordinator.acquire_pulse_turn(timeout_sec=15.0)

        announcement = generate_unprompted_speech(event_type, event_context)
        if not announcement:
            return ""

        print(f"\n\n[JARVIS UNPROMPTED PULSE - {event_type.upper()}]")
        print(f"JARVIS: {announcement}\n")

        # Save to SQLite database so conversation memory knows JARVIS spoke
        memory.append_message("assistant", announcement)

        # Update in-memory history list if available
        if isinstance(self.history_ref, list):
            self.history_ref.append({"role": "assistant", "content": announcement})

        # Deliver audio or trigger callback
        if self.on_speak:
            try:
                self.on_speak(announcement)
            except Exception as e:
                print(f"[PULSE SPEAK ERROR] {e}")

        return announcement

    def _loop(self) -> None:
        """Silent, lightweight loop running in the background thread."""
        # Initial grace period so startup greeting completes without interruption
        time.sleep(8)

        while self._running:
            try:
                now = time.time()

                for trigger in self.triggers:
                    if not self._running:
                        break

                    if trigger.can_check(now):
                        should_fire, event_type, event_context = trigger.evaluate(now)
                        if should_fire:
                            self._dispatch_event(event_type, event_context)

            except Exception as e:
                print(f"[PULSE LOOP ERROR] {e}")

            # Sleep 2 seconds between tick evaluations (negligible CPU consumption)
            time.sleep(2.0)

    def get_status(self) -> dict:
        """Returns diagnostic status of the Pulse agent and its triggers."""
        now_dt = datetime.datetime.now()
        return {
            "running": self._running,
            "briefing_target_time": self.briefing_trigger.target_time_str,
            "last_briefed_date": self.briefing_trigger.last_briefed_date,
            "known_models": list(self.model_trigger.known_models),
            "pending_reminders_count": len(memory.get_pending_reminders()),
            "current_time": now_dt.strftime("%Y-%m-%d %H:%M:%S"),
        }


# Global PulseEngine instance
pulse_agent: PulseEngine | None = None


def get_pulse_agent() -> PulseEngine | None:
    return pulse_agent


def init_pulse_agent(
    on_speak: Callable[[str], None] | None = None,
    history_ref: list | None = None,
    is_text_mode: bool = False,
) -> PulseEngine:
    global pulse_agent
    if pulse_agent is None:
        pulse_agent = PulseEngine(
            on_speak=on_speak, history_ref=history_ref, is_text_mode=is_text_mode
        )
    else:
        if on_speak:
            pulse_agent.on_speak = on_speak
        if history_ref is not None:
            pulse_agent.history_ref = history_ref
        pulse_agent.is_text_mode = is_text_mode
    return pulse_agent

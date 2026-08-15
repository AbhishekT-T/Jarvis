import datetime
import threading
import time
import shutil
import psutil

import sys

import llm
import memory

TEXT_MODE = "--text" in sys.argv

if not TEXT_MODE:
    import sounddevice as sd
    import stt
    import tts

EXIT_COMMANDS = {"quit", "exit", "stop", "goodbye"}
FORGET_COMMANDS = {
    "forget", "forget everything", "clear memory", "clear history", "wipe memory",
    "erase your memory", "delete your memory",
}


def _print_audio_info() -> None:
    """Shows which microphone is in use so bad capture can be diagnosed."""
    if TEXT_MODE:
        return
    try:
        device = sd.query_devices(kind="input")
        print(f"Audio input: {device['name']} | {device.get('default_samplerate', 44100):.0f} Hz")
        print(f"Audio output: {sd.query_devices(kind='output')['name']}")
    except Exception as e:
        print(f"Could not query audio devices: {e}")


def _greeting() -> str:
    """Returns a time-of-day greeting so JARVIS feels aware of the moment."""
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    return "Good evening"


def _normalize(text: str) -> str:
    return text.lower().strip(" ,.?!")


def _monitor_system() -> None:
    """Continuously monitors system vitals in the background and announces warnings if thresholds are exceeded.
    """
    # Wait 10 seconds initially so it doesn't speak over the startup greeting
    time.sleep(10)
    while True:
        try:
            # Check vitals every 60 seconds
            time.sleep(60)
            
            # 1. Check Disk Space on C:
            try:
                _, _, free = shutil.disk_usage("C:\\")
                free_gb = free / (1024 ** 3)
                if free_gb < 5.0:
                    msg = f"System alert, sir. Storage space on drive C is critically low, with only {free_gb:.1f} gigabytes remaining."
                    print(f"\n[SYSTEM MONITOR ALERT] {msg}\n")
                    if not TEXT_MODE:
                        tts.speak(msg)
                    continue
            except Exception:
                pass
                
            # 2. Check CPU utilization
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 90.0:
                msg = f"System alert, sir. CPU utilization is critically high at {cpu:.0f} percent."
                print(f"\n[SYSTEM MONITOR ALERT] {msg}\n")
                if not TEXT_MODE:
                    tts.speak(msg)
                continue
                
            # 3. Check Memory (RAM) utilization
            ram = psutil.virtual_memory().percent
            if ram > 90.0:
                msg = f"System alert, sir. Memory utilization is critically high at {ram:.0f} percent."
                print(f"\n[SYSTEM MONITOR ALERT] {msg}\n")
                if not TEXT_MODE:
                    tts.speak(msg)
                continue
                
        except Exception:
            pass


def main() -> None:
    # Restore memory from previous sessions so JARVIS "remembers" you.
    history = memory.load_history()

    _print_audio_info()
    
    # Start background live system monitor thread
    monitor_thread = threading.Thread(target=_monitor_system, daemon=True)
    monitor_thread.start()
    
    if TEXT_MODE:
        mode_choice = "0"
    else:
        print("\n=======================================================")
        print("SELECT INPUT MODE:")
        print("  [1] Wake Word Only ('Hey Jarvis')")
        print("  [2] Push-to-Talk Only (Hold CTRL)")
        print("  [3] Combined: Wake Word OR Push-to-Talk (Default)")
        print("  [4] Always Listening (Classic VAD)")
        print("=======================================================")
        mode_choice = input("Enter option (1/2/3/4) [3]: ").strip()
        if mode_choice not in {"1", "2", "3", "4"}:
            mode_choice = "3"
        
    detector = None
    if mode_choice in {"1", "3"} and not TEXT_MODE:
        from wakeword import WakeWordDetector
        detector = WakeWordDetector()
        
    greeting_msg = f"{_greeting()}, sir. Jarvis online."
    if not TEXT_MODE:
        tts.speak(greeting_msg)
    else:
        print(f"JARVIS: {greeting_msg}")

    print("JARVIS is active. (Say 'exit' or 'quit' to stop).")
    
    if TEXT_MODE:
        print("Listening: Text mode active. Type your message...")
    elif mode_choice == "3":
        print("Listening: Say 'Hey Jarvis' OR Hold [CTRL] key down to speak...")
    elif mode_choice == "1":
        print("Listening: Say 'Hey Jarvis' to speak...")
    elif mode_choice == "2":
        print("Listening: Hold [CTRL] key down to speak...")
    else:
        print("Listening: Always listening...")

    while True:
        try:
            user_text = ""
            if TEXT_MODE:
                user_text = input("\nYou: ").strip()
            elif mode_choice == "1":
                detector.listen_for_wake_word()
                user_text = stt.listen_and_transcribe()
            elif mode_choice == "2":
                user_text = stt.listen_and_transcribe_ptt(key="ctrl")
            elif mode_choice == "3":
                trigger = detector.listen_for_wake_word_or_ptt(ptt_key="ctrl")
                if trigger == "ptt":
                    user_text = stt.listen_and_transcribe_ptt(key="ctrl")
                else:
                    user_text = stt.listen_and_transcribe()
            else:
                user_text = stt.listen_and_transcribe()

            if not user_text:
                continue

            # A single "utterance" can chain when the user interrupts JARVIS.
            while user_text:
                if _normalize(user_text) in EXIT_COMMANDS:
                    goodbye_msg = "Goodbye, sir."
                    print(f"JARVIS: {goodbye_msg}")
                    if not TEXT_MODE:
                        tts.speak(goodbye_msg)
                    return

                if _normalize(user_text) in FORGET_COMMANDS:
                    reply = "Conversation memory cleared, sir."
                    history = []
                    memory.clear_history()
                    print(f"JARVIS: {reply}")
                    if not TEXT_MODE:
                        tts.speak(reply)
                    break

                if not TEXT_MODE:
                    print(f"You: {user_text}")

                # Save user message to database in real-time
                memory.append_message('user', user_text)

                # Query LLM with history
                response = llm.query_jarvis(user_text, history)
                print(f"JARVIS: {response}")

                # Save assistant response to database in real-time
                memory.append_message('assistant', response)

                # Update local in-memory history list
                history.append({'role': 'user', 'content': user_text})
                history.append({'role': 'assistant', 'content': response})

                # Speak; if the user interrupts, JARVIS stops instantly.
                # The audio that overlapped his speech is polluted by his own
                # voice, so re-listen once he's silent for a clean capture.
                if not TEXT_MODE:
                    if tts.speak(response):
                        print("\n(You interrupted - JARVIS is listening...)\n")
                        user_text = stt.listen_and_transcribe(max_wait=8.0)
                        if not user_text:
                            break
                        continue
                
                break  # Exit the inner loop if not interrupted to listen again


        except KeyboardInterrupt:
            print("\nOffline.")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")


if __name__ == "__main__":
    main()

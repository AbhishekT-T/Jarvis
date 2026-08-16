import datetime
import sys

import llm
import memory
import pulse

TEXT_MODE = "--text" in sys.argv

if not TEXT_MODE:
    # pyrefly: ignore [missing-import]
    import sounddevice as sd
    import stt
    import tts

EXIT_COMMANDS = {"quit", "exit", "stop", "goodbye"}
FORGET_COMMANDS = {
    "forget",
    "forget everything",
    "clear memory",
    "clear history",
    "wipe memory",
    "erase your memory",
    "delete your memory",
}


def _print_audio_info() -> None:
    """Shows which microphone is in use so bad capture can be diagnosed."""
    if TEXT_MODE:
        return
    try:
        device = sd.query_devices(kind="input")
        print(
            f"Audio input: {device['name']} | {device.get('default_samplerate', 44100):.0f} Hz"
        )
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


def main() -> None:
    # Restore memory from previous sessions so JARVIS "remembers" you.
    history = memory.load_history()

    _print_audio_info()

    # Define proactive audio callback for unprompted Pulse announcements
    def _on_pulse_speak(announcement_text: str) -> None:
        if not TEXT_MODE:
            tts.speak(announcement_text)

    # Initialize and start the autonomous Background Cron-Agent (The "Pulse")
    pulse_engine = pulse.init_pulse_agent(
        on_speak=_on_pulse_speak,
        history_ref=history,
        is_text_mode=TEXT_MODE,
    )
    pulse_engine.start()

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
                pulse.coordinator.start_user_interaction()
                user_text = stt.listen_and_transcribe()
            elif mode_choice == "2":
                pulse.coordinator.start_user_interaction()
                user_text = stt.listen_and_transcribe_ptt(key="ctrl")
            elif mode_choice == "3":
                trigger = detector.listen_for_wake_word_or_ptt(ptt_key="ctrl")
                pulse.coordinator.start_user_interaction()
                if trigger == "ptt":
                    user_text = stt.listen_and_transcribe_ptt(key="ctrl")
                else:
                    user_text = stt.listen_and_transcribe()
            else:
                pulse.coordinator.start_user_interaction()
                user_text = stt.listen_and_transcribe()

            if not user_text:
                pulse.coordinator.end_user_interaction()
                continue

            pulse.coordinator.start_user_interaction()

            # A single "utterance" can chain when the user interrupts JARVIS.
            while user_text:
                if _normalize(user_text) in EXIT_COMMANDS:
                    goodbye_msg = "Goodbye, sir."
                    print(f"JARVIS: {goodbye_msg}")
                    if not TEXT_MODE:
                        tts.speak(goodbye_msg)
                    pulse_engine.stop()
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
                memory.append_message("user", user_text)

                # Query LLM with history
                response = llm.query_jarvis(user_text, history)
                print(f"JARVIS: {response}")

                # Save assistant response to database in real-time
                memory.append_message("assistant", response)

                # Update local in-memory history list
                history.append({"role": "user", "content": user_text})
                history.append({"role": "assistant", "content": response})

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

            pulse.coordinator.end_user_interaction()

        except KeyboardInterrupt:
            print("\nOffline.")
            pulse_engine.stop()
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            pulse.coordinator.end_user_interaction()


if __name__ == "__main__":
    main()

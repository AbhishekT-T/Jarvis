import sys
import stt
import llm
import tts

EXIT_COMMANDS = {"quit", "exit", "stop", "goodbye"}

def main() -> None:
    # Acknowledge start
    tts.speak("Jarvis online.")
    print("JARVIS is active. Speak clearly. (Say 'exit' or 'quit' to stop).")
    
    # Store conversation history
    history = []
    
    while True:
        try:
            print("\nListening...")
            user_text = stt.listen_and_transcribe()
            if not user_text:
                continue
                
            print(f"You: {user_text}")
            
            # Check for exit command
            if user_text.lower().strip(" ,.?!") in EXIT_COMMANDS:
                goodbye_msg = "Goodbye, sir."
                print(f"JARVIS: {goodbye_msg}")
                tts.speak(goodbye_msg)
                break
                
            # Query LLM with history
            response = llm.query_jarvis(user_text, history)
            print(f"JARVIS: {response}")
            
            # Speak the response
            tts.speak(response)
            
            # Save interaction to conversation history
            history.append({'role': 'user', 'content': user_text})
            history.append({'role': 'assistant', 'content': response})
            if len(history) > 10:
                history = history[-10:]
                
        except KeyboardInterrupt:
            print("\nOffline.")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")

if __name__ == "__main__":
    main()

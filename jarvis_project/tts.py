import pyttsx3

def speak(text: str) -> None:
    """Initializes the pyttsx3 engine, sets the speech rate to 170,
    and speaks the provided text out loud.
    """
    engine = pyttsx3.init()
    engine.setProperty('rate', 170)
    engine.say(text)
    engine.runAndWait()

if __name__ == "__main__":
    speak("Voice synthesis protocols are online, sir.")

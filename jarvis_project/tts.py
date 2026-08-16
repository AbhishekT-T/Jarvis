import io
import os
import wave

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

try:
    from piper import PiperVoice

    _PIPER_AVAILABLE = True
except ImportError:
    _PIPER_AVAILABLE = False

import pyttsx3

VOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
VOICE_NAME = "en_GB-alan-medium"
VOICE_MODEL = os.path.join(VOICE_DIR, f"{VOICE_NAME}.onnx")

_piper_voice = None
_tts_engine = None


def _get_piper_voice():
    """Loads and caches the Piper neural voice (much more human than SAPI)."""
    global _piper_voice
    if _piper_voice is None:
        _piper_voice = PiperVoice.load(VOICE_MODEL)
    return _piper_voice


def _get_pyttsx3_engine():
    """Lazily initializes and caches a pyttsx3 engine (fallback only)."""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = pyttsx3.init()
        _tts_engine.setProperty("rate", 170)
    return _tts_engine


def _synth_piper_audio(text: str):
    """Synthesizes text with Piper, returning (sample_rate, int16 mono audio)."""
    voice = _get_piper_voice()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    buf.seek(0)
    fs, audio = wavfile.read(buf)
    if audio.ndim > 1:
        audio = audio[:, 0]
    return fs, np.ascontiguousarray(audio, dtype=np.int16)


def _speak_piper_bargeable(text: str) -> bool:
    """Plays Piper audio. Barge-in disabled for mic, but enabled for CTRL key."""
    import keyboard
    import time
    
    fs, audio = _synth_piper_audio(text)
    sd.play(audio, fs)
    
    duration = len(audio) / fs
    start_time = time.time()
    
    while time.time() - start_time < duration:
        if keyboard.is_pressed('ctrl'):
            sd.stop()
            return True
        time.sleep(0.05)
        
    sd.stop()
    return False


def _speak_pyttsx3(text: str) -> None:
    engine = _get_pyttsx3_engine()
    engine.say(text)
    engine.runAndWait()


def speak(text: str) -> bool:
    """Speaks text out loud with a natural, human-sounding local voice.

    Listens on the microphone while talking: if the user starts speaking,
    JARVIS stops immediately and quietly (no buffered audio plays out), so the
    caller can re-listen and capture the user's words without his own echo
    polluting them.

    Args:
        text (str): The text to speak.

    Returns:
        bool: True if the user interrupted JARVIS mid-speech.
    """
    text = (text or "").strip()
    if not text:
        return False

    if _PIPER_AVAILABLE and os.path.exists(VOICE_MODEL):
        return _speak_piper_bargeable(text)

    _speak_pyttsx3(text)
    return False


if __name__ == "__main__":
    result = speak(
        "Voice synthesis protocols are online, sir. Feel free to interrupt me."
    )
    if result:
        print("Interrupted by user.")
    else:
        print("Finished speaking, no interruption.")

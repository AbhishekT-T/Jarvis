import io
import os
import wave

import numpy as np
import sounddevice as sd
from scipy.io import wavfile

from vad import SpeechInterruptMonitor

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
        _tts_engine.setProperty('rate', 170)
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
    """Plays Piper audio while listening for the user to interrupt.

    On interrupt, playback is aborted instantly so no echo tail continues.

    Returns:
        bool: True if the user interrupted JARVIS mid-speech.
    """
    monitor = SpeechInterruptMonitor()
    if not monitor.arm():
        # Mic unavailable - fall back to plain blocking playback.
        monitor.close()
        fs, audio = _synth_piper_audio(text)
        sd.play(audio, fs)
        sd.wait()
        return False

    try:
        fs, audio = _synth_piper_audio(text)
        chunk = 2048  # ~93 ms at 22 kHz -> fast interrupt checks
        interrupted = False

        try:
            with sd.OutputStream(samplerate=fs, channels=1, dtype='int16') as out:
                for start in range(0, len(audio), chunk):
                    if monitor.was_interrupted():
                        interrupted = True
                        out.abort()  # stop playback NOW, don't flush buffered audio
                        break
                    out.write(audio[start:start + chunk])
                if not interrupted:
                    # A short grace window catches speech that starts as JARVIS finishes.
                    interrupted = monitor.wait(timeout=0.1)
        except Exception:
            # Stream playback failed - fall back to plain blocking playback.
            sd.play(audio, fs)
            sd.wait()
            interrupted = False

        return interrupted
    finally:
        monitor.close()


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
    result = speak("Voice synthesis protocols are online, sir. Feel free to interrupt me.")
    if result:
        print("Interrupted by user.")
    else:
        print("Finished speaking, no interruption.")

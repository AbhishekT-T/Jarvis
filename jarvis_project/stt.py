import os

import numpy as np
from scipy.io import wavfile
from faster_whisper import WhisperModel
import keyboard
import sounddevice as sd
import time

import noisereduce as nr

from vad import UtteranceRecorder

_model = None
TEMP_WAV = "temp.wav"

# Set to False if noise reduction feels too slow on your CPU.
USE_NOISE_REDUCTION = True


def get_whisper_model() -> WhisperModel:
    """Loads and caches the WhisperModel in memory to prevent reloading from disk.
    """
    global _model
    if _model is None:
        _model = WhisperModel("base.en", device="cpu", compute_type="int8")
    return _model


def _normalize(audio: np.ndarray, target_peak: float = 0.9) -> np.ndarray:
    """Scales audio up (capped) so quiet mics aren't transcribed poorly."""
    audio = audio.astype(np.float32)
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak < 1e-6:
        return audio.astype(np.int16)
    gain = min(target_peak * 32767.0 / peak, 5.0)
    return np.clip(audio * gain, -32768, 32767).astype(np.int16)


def _reduce_noise(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Applies stationary noise reduction using leading silence as the reference.

    Only runs if the first ~0.25s is genuinely quiet, so speech at the very
    start isn't mistaken for noise.
    """
    noise_len = int(0.25 * sample_rate)
    if len(audio) < noise_len * 2:
        return audio
    lead = audio[:noise_len]
    lead_rms = float(np.sqrt(np.mean(np.square(lead.astype(np.float64)))))
    if lead_rms > 60:  # leading audio is speech, not noise -> skip
        return audio
    reduced = nr.reduce_noise(
        y=audio.astype(np.float32),
        y_noise=lead.astype(np.float32),
        sr=sample_rate,
        stationary=True,
    )
    return np.clip(reduced, -32768, 32767).astype(np.int16)


def transcribe_audio(audio, sample_rate: int = 16000) -> str:
    """Cleans and transcribes numpy int16 audio using faster-whisper on CPU.

    Args:
        audio (np.ndarray): Mono audio samples.
        sample_rate (int): Sample rate of the audio.

    Returns:
        str: The transcribed text (empty if nothing was heard).
    """
    if audio is None or len(audio) == 0:
        return ""

    audio = _normalize(audio, sample_rate)
    if USE_NOISE_REDUCTION:
        audio = _reduce_noise(audio, sample_rate)

    wavfile.write(TEMP_WAV, sample_rate, audio)
    try:
        model = get_whisper_model()
        segments, _ = model.transcribe(TEMP_WAV, beam_size=5)
        return " ".join(segment.text for segment in segments).strip()
    finally:
        if os.path.exists(TEMP_WAV):
            try:
                os.remove(TEMP_WAV)
            except OSError:
                pass


def listen_and_transcribe(max_wait: float = 8.0) -> str:
    """Records a complete spoken utterance and transcribes it.

    Uses voice-activity detection: waits for speech to start, records until a
    pause, then returns the transcription. No fixed-length window, so long
    sentences are captured fully.

    Args:
        max_wait (float): Seconds to wait for speech before giving up.

    Returns:
        str: The transcribed text (empty if nothing was heard).
    """
    recorder = UtteranceRecorder()
    audio = recorder.record(max_wait=max_wait)
    if audio is None:
        return ""
    return transcribe_audio(audio)


def listen_and_transcribe_ptt(key: str = "ctrl") -> str:
    """Records audio while a hotkey is pressed and transcribes it.

    Args:
        key (str): The hotkey to trigger recording (e.g. "ctrl", "space").

    Returns:
        str: The transcribed text.
    """
    print(f"\nHOLD [{key.upper()}] TO TALK...")
    
    # Wait for the key to be pressed
    while not keyboard.is_pressed(key):
        time.sleep(0.05)
        
    print("Recording... Speak now! Release key to send.")
    audio_chunks = []
    
    def callback(indata, frames, time_info, status):
        audio_chunks.append(indata.copy())
        
    stream = sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype='int16',
        blocksize=1024,
        callback=callback
    )
    
    with stream:
        while keyboard.is_pressed(key):
            time.sleep(0.05)
            
    print("Recording stopped. Transcribing...")
    if not audio_chunks:
        return ""
        
    audio = np.concatenate(audio_chunks)[:, 0]
    return transcribe_audio(audio)


if __name__ == "__main__":
    print("Speak now - recording until you pause...")
    text = listen_and_transcribe()
    print("Transcription:")
    print(text)


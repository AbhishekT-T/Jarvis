import os
import sounddevice as sd
from scipy.io import wavfile
from faster_whisper import WhisperModel

def listen_and_transcribe() -> str:
    """Records 5 seconds of audio from the default microphone,
    saves it to a temporary file, and transcribes it using faster-whisper on CPU.
    """
    fs = 16000  # Sample rate
    seconds = 5  # Duration of recording
    temp_filename = "temp.wav"

    # 1. Record audio
    audio = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()  # Wait until the recording is finished

    # 2. Save temporary wav file
    wavfile.write(temp_filename, fs, audio)

    # 3. Load Whisper model forcing CPU and int8 quantization
    # This prevents using GPU VRAM (reserved for Ollama)
    model = WhisperModel("base.en", device="cpu", compute_type="int8")

    # 4. Transcribe audio
    segments, info = model.transcribe(temp_filename, beam_size=5)
    
    # Collect transcription segments
    transcription = " ".join([segment.text for segment in segments]).strip()

    # 5. Clean up temporary wav file
    if os.path.exists(temp_filename):
        try:
            os.remove(temp_filename)
        except Exception:
            pass

    return transcription

if __name__ == "__main__":
    print("Listening for 5 seconds...")
    text = listen_and_transcribe()
    print("Transcription:")
    print(text)

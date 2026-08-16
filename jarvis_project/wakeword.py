import sounddevice as sd
from openwakeword.model import Model

SAMPLE_RATE = 16000
CHUNK_SIZE = 1280  # openWakeWord expects chunks of 1280 samples (80 ms at 16kHz)


class WakeWordDetector:
    def __init__(self, model_name="hey_jarvis", threshold=0.5):
        self.model_name = model_name
        self.threshold = threshold
        # Initialize the openWakeWord model
        self.oww_model = Model(wakeword_models=[model_name], inference_framework="onnx")

    def listen_for_wake_word(self) -> bool:
        """Blocks until the wake word is detected."""
        print(f"Waiting for wake word '{self.model_name}'...")

        # Audio buffer to collect samples if needed
        # openWakeWord expects 16-bit mono PCM (int16)
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=CHUNK_SIZE
        )

        with stream:
            while True:
                # Read a chunk from the stream
                data, overflowed = stream.read(CHUNK_SIZE)
                if overflowed:
                    continue

                # Reshape to 1D array
                chunk = data[:, 0]

                # Get prediction from openWakeWord model
                # The model expects a 1D numpy array of 1280 samples
                prediction = self.oww_model.predict(chunk)

                # Check prediction confidence
                prob = prediction.get(self.model_name, 0.0)
                if prob >= self.threshold:
                    print(
                        f"\n[WAKE WORD] Detected '{self.model_name}' with confidence {prob:.2f}!"
                    )
                    return True

    def listen_for_wake_word_or_ptt(self, ptt_key="ctrl") -> str:
        """Blocks until either the wake word is detected or the PTT key is pressed."""

        import keyboard

        print(
            f"Waiting for wake word '{self.model_name}' OR hold [{ptt_key.upper()}] to talk..."
        )

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=CHUNK_SIZE
        )

        with stream:
            while True:
                if keyboard.is_pressed(ptt_key):
                    return "ptt"

                data, overflowed = stream.read(CHUNK_SIZE)
                if overflowed:
                    continue

                chunk = data[:, 0]
                prediction = self.oww_model.predict(chunk)
                prob = prediction.get(self.model_name, 0.0)
                if prob >= self.threshold:
                    print(
                        f"\n[WAKE WORD] Detected '{self.model_name}' with confidence {prob:.2f}!"
                    )
                    return "wakeword"

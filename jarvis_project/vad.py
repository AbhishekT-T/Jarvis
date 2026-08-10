import threading
import time
from collections import deque

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
BLOCK_SIZE = 1024                 # ~64 ms per block
RMS_THRESHOLD = 500               # int16 amplitude; raise if speakers echo-trigger it
MIN_SPEECH_BLOCKS = 3             # ~192 ms of sustained loud audio before interrupting
MAX_BUFFER_BLOCKS = int(12 * SAMPLE_RATE / BLOCK_SIZE)  # keep ~12 s of rolling audio


class SpeechInterruptMonitor:
    """Listens on the microphone while JARVIS is speaking.

    When the user starts talking, it trips an event (barge-in) and keeps a
    rolling buffer so the interjection can be transcribed afterwards.
    """

    def __init__(self):
        self._stream = None
        self._interrupt = threading.Event()
        self._lock = threading.Lock()
        self._samples = []
        self._speech_blocks = 0
        self._triggered = False
        self._trigger_start = 0

    def _callback(self, indata, frames, time_info, status):
        chunk = indata[:, 0].copy()
        rms = float(np.sqrt(np.mean(np.square(chunk.astype(np.float64)))))
        with self._lock:
            self._samples.append(chunk)
            if len(self._samples) > MAX_BUFFER_BLOCKS:
                del self._samples[:-MAX_BUFFER_BLOCKS]

            if not self._triggered:
                if rms > RMS_THRESHOLD:
                    if self._speech_blocks == 0:
                        self._trigger_start = len(self._samples) - 1
                    self._speech_blocks += 1
                    if self._speech_blocks >= MIN_SPEECH_BLOCKS:
                        self._triggered = True
                        self._interrupt.set()
                else:
                    self._speech_blocks = 0

    def arm(self) -> bool:
        """Starts the microphone monitor. Returns True if it's active."""
        self.close()
        self._interrupt.clear()
        self._triggered = False
        self._speech_blocks = 0
        self._trigger_start = 0
        self._samples = []
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype='int16',
                blocksize=BLOCK_SIZE,
                callback=self._callback,
            )
            self._stream.start()
            return True
        except Exception:
            self._stream = None
            return False

    def was_interrupted(self) -> bool:
        return self._interrupt.is_set()

    def wait(self, timeout: float) -> bool:
        return self._interrupt.wait(timeout)

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None


class UtteranceRecorder:
    """Records a complete spoken utterance, start to end.

    Waits for the user to begin talking, captures everything until they pause
    (configurable silence gap), then returns the audio. No fixed-length window,
    so nobody gets cut off mid-sentence.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, block_size: int = BLOCK_SIZE):
        self.sample_rate = sample_rate
        self.block_size = block_size

    def record(self, max_wait: float = 8.0, min_silence: float = 0.7,
               pre_roll: float = 0.5, max_utterance: float = 15.0):
        """Blocks until an utterance is captured.

        Args:
            max_wait: Seconds to wait for speech to start before giving up.
            min_silence: Seconds of quiet that mark the end of the utterance.
            pre_roll: Seconds of audio kept before speech onset (noise reference).
            max_utterance: Hard cap on a single utterance length.

        Returns:
            np.ndarray | None: int16 mono audio, or None if no speech in max_wait.
        """
        fs = self.sample_rate
        block = self.block_size
        pre_roll_blocks = max(1, int(pre_roll * fs / block))
        min_silence_blocks = max(1, int(min_silence * fs / block))
        max_utterance_seconds = max_utterance

        ring = deque(maxlen=pre_roll_blocks)
        utterance = []
        speech_blocks = 0
        silence_blocks = 0
        state = "waiting"
        started = time.monotonic()
        utterance_started = None

        stream = sd.InputStream(
            samplerate=fs, channels=1, dtype="int16", blocksize=block
        )
        stream.start()
        try:
            while True:
                data, _ = stream.read(block)
                chunk = data[:, 0]
                rms = float(np.sqrt(np.mean(np.square(chunk.astype(np.float64)))))

                if state == "waiting":
                    ring.append(chunk)
                    if rms > RMS_THRESHOLD:
                        speech_blocks += 1
                        if speech_blocks >= MIN_SPEECH_BLOCKS:
                            state = "recording"
                            utterance_started = time.monotonic()
                            utterance = list(ring) + [chunk]
                            silence_blocks = 0
                    else:
                        speech_blocks = 0
                    if time.monotonic() - started > max_wait:
                        break
                else:  # recording
                    utterance.append(chunk)
                    if rms > RMS_THRESHOLD:
                        silence_blocks = 0
                    else:
                        silence_blocks += 1
                        if silence_blocks >= min_silence_blocks:
                            break
                    if time.monotonic() - utterance_started > max_utterance_seconds:
                        break
        finally:
            stream.stop()
            stream.close()

        if state == "recording" and utterance:
            return np.concatenate(utterance)
        return None

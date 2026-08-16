import sys
import time
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
BLOCK_SIZE = 1024

print("Available devices:")
print(sd.query_devices())
print("\nDefault input device:")
print(sd.query_devices(kind="input"))

print("\nStarting stream...")
try:
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=BLOCK_SIZE
    )
    with stream:
        print("Stream started. Please speak or make noise for 5 seconds...")
        for _ in range(50):
            data, overflow = stream.read(BLOCK_SIZE)
            chunk = data[:, 0]
            rms = float(np.sqrt(np.mean(np.square(chunk.astype(np.float64)))))
            print(f"RMS: {rms:.2f}, Max: {np.max(chunk)}, Min: {np.min(chunk)}")
except Exception as e:
    print(f"Error: {e}")

#!/usr/bin/env python3
"""
Create a simple test audio file for POC testing
"""
import wave
import struct
import math

# Audio parameters
sample_rate = 44100
duration = 5  # seconds
frequency = 440  # A4 note

# Generate sine wave
num_samples = sample_rate * duration
samples = []

for i in range(num_samples):
    t = float(i) / sample_rate
    value = math.sin(2 * math.pi * frequency * t)
    # Convert to 16-bit PCM
    packed_value = struct.pack('h', int(value * 32767.0))
    samples.append(packed_value)

# Write WAV file
with wave.open('test_audio.wav', 'wb') as wav_file:
    wav_file.setnchannels(1)  # mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(sample_rate)
    wav_file.writeframes(b''.join(samples))

print("Created test_audio.wav - 5 second 440Hz tone")
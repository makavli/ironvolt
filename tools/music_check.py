"""Renders every song to shots/music_<name>.wav and prints build time, the longest single build step
(what a browser frame would stall on), loudness and peak.   python tools/music_check.py"""
import math
import os
import sys
import time
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ironvolt import music  # noqa: E402

os.makedirs("shots", exist_ok=True)
for name in music.SONGS:
    t, worst, gen = time.perf_counter(), 0.0, music.build(name)
    while True:
        a = time.perf_counter()
        try:
            next(gen)
        except StopIteration as done:
            data = done.value
            break
        worst = max(worst, time.perf_counter() - a)
    left = data[0::2]
    rms = math.sqrt(sum(x * x for x in left) / len(left))
    print("%-6s %5.2f s build, longest step %4.1f ms, %4.1f s of music, rms %5d, peak %5d"
          % (name, time.perf_counter() - t, worst * 1000, len(left) / music.RATE, rms, max(map(abs, data))))
    with wave.open(os.path.join("shots", "music_%s.wav" % name), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(music.RATE)
        w.writeframes(data.tobytes())

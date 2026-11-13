"""Renders every song and encodes it to Ogg Vorbis for the browser build (needs ffmpeg).

A browser plays the game and its sound on one thread, so building the songs there made the sound tick until they
were done. The browser build ships these files instead; the desktop game still builds the songs itself.

    python tools/music_bake.py OUT_DIR
"""
import os
import subprocess
import sys
import tempfile
import wave

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from ironvolt import music  # noqa: E402

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
with tempfile.TemporaryDirectory() as tmp:
    for name in music.SONGS:
        wav = os.path.join(tmp, name + ".wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(music.RATE)
            w.writeframes(music.render(name).tobytes())
        ogg = os.path.join(out, name + ".ogg")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "5", ogg], check=True)
        print("%-6s %4d KB" % (name, os.path.getsize(ogg) // 1024))

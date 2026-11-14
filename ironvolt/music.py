"""IRONVOLT's soundtrack, synthesized in code: a stage theme and a boss theme, in stereo.

A song is a list of sections: one chord per bar, a backing style and an optional lead line. A bar's
backing (drums, rolling bass, detuned pad and arpeggio, all pumped by the kick) depends only on its
chord and style, so each one is rendered once and copied. The lead, a ping-pong delay and a
soft-clipping master then run once over the whole song. render() returns 16-bit stereo, interleaved.

build() is the same work as a generator that yields every few thousand samples: a browser has no
threads, so audio.tick() runs it a few milliseconds a frame and the game never stalls.
"""

import math
import random
from array import array

RATE = 22050
NOTE = {n: i for i, n in enumerate("C C# D D# E F F# G G# A A# B".split())}
CHORDS = {"Am": (57, (0, 3, 7)), "Dm": (62, (0, 3, 7)), "F": (53, (0, 4, 7)), "C": (60, (0, 4, 7)),
          "G": (55, (0, 4, 7)), "E": (52, (0, 4, 7)), "Bb": (58, (0, 4, 7)),
          "Em": (52, (0, 3, 7)), "D": (62, (0, 4, 7)), "B": (59, (0, 4, 7)),
          "A": (57, (0, 4, 7)), "Gm": (55, (0, 3, 7)), "Eb": (63, (0, 4, 7)),
          "Cm": (60, (0, 3, 7)), "Ab": (56, (0, 4, 7)), "Fm": (53, (0, 3, 7)), "Db": (61, (0, 4, 7))}   # pad root (MIDI), intervals
STYLES = {   # drums, bass notes a bar (0, 8 or 16), pad brightness (low-pass Hz), arpeggio
    "intro": ("half", 8, 900, True),
    "drive": ("full", 8, 1500, True),
    "lift": ("full", 8, 2400, True),
    "break": ("none", 0, 1100, True),
    "rise": ("rise", 0, 1600, True),
    "boss": ("boss", 8, 800, True),
    "title": ("half", 8, 1300, False),
}

# Leads: one token per 16th note. A note starts, "-" holds it, "." rests.
HOOK = ["E5 - - - . E5 D5 E5 A5 - - - G5 - E5 -", "F5 - - - E5 - C5 - . C5 D5 - E5 - - -",
        "G5 - - - . G5 F5 G5 C6 - - - B5 - G5 -", "B5 - - - A5 - G5 - D5 - - - - - . .",
        "E5 - - - . E5 D5 E5 A5 - - - G5 - E5 -", "F5 - - - E5 - C5 - A5 - - - G5 - F5 -",
        "E5 - - - G5 - C6 - B5 - - - G5 - E5 -", "D5 - - - - - B4 - D5 - E5 - - - - -"]
LIFT = ["D5 - - - - - F5 - A5 - - - - - G5 -", "E5 - - - - - - - C5 - D5 - E5 - - -",
        "F5 - - - - - A5 - C6 - - - - - A5 -", "G#5 - - - - - - - B5 - - - G#5 - E5 -",
        "D5 - - - - - F5 - A5 - - - D6 - C6 -", "C6 - - - B5 - A5 - E5 - - - - - . .",
        "F5 - - - A5 - C6 - E6 - - - D6 - C6 -", "B5 - - - - - - - G#5 - - - - - - -"]
SIEGE = ["A5 - - - . A5 C6 - B5 - A5 - G5 - E5 -", "F5 - - - . F5 A#5 - A5 - G5 - F5 - D5 -",
         "E5 - - - . E5 A5 - C6 - - - B5 - A5 -", "B5 - - - D6 - - - G#5 - - - E5 - . .",
         "A5 - - - . A5 C6 - B5 - A5 - G5 - E5 -", "D6 - - - C6 - A#5 - A5 - - - F5 - A5 -",
         "G5 - - - C6 - E6 - D6 - - - C6 - G5 -", "G#5 - - - B5 - D6 - E6 - - - - - . ."]

# Mission 2, the prisoner line: E minor, a rolling train beat; the boss in E with a Phrygian F.
RAIL = ["E5 - - . G5 - A5 - B5 - - - A5 - G5 -", "E5 - - - . E5 G5 E5 C5 - - - D5 - E5 -",
        "D5 - - . G5 - B5 - D6 - - - B5 - G5 -", "F#5 - - - A5 - - - D5 - - - . . . .",
        "E5 - - . G5 - A5 - B5 - - - A5 - G5 -", "C6 - - - B5 - G5 - E5 - - - G5 - A5 -",
        "B5 - - - D6 - B5 - G5 - - - B5 - D6 -", "D#6 - - - - - B5 - F#5 - - - D#5 - - -"]
SIGNAL = ["G5 - - - - - E5 - C5 - - - E5 - G5 -", "A5 - - - - - F#5 - D5 - - - F#5 - A5 -",
          "B5 - - - - - - - G5 - A5 - B5 - - -", "E6 - - - D6 - B5 - G5 - - - - - . .",
          "G5 - - - - - E5 - C6 - - - B5 - G5 -", "A5 - - - - - D6 - F#5 - - - A5 - D6 -",
          "D#6 - - - - - - - B5 - - - F#5 - - -", "B5 - - - - - - - - - - - . . . ."]
RAM = ["E5 - - - . E5 G5 - F5 - E5 - D5 - B4 -", "F5 - - - . F5 A5 - G5 - F5 - E5 - C5 -",
       "E5 - - - . E5 B5 - C6 - - - B5 - G5 -", "D#5 - - - F#5 - - - B5 - - - - - . .",
       "E5 - - - . E5 G5 - F5 - E5 - D5 - B4 -", "C6 - - - B5 - A5 - G5 - - - F5 - A5 -",
       "G5 - - - B5 - D6 - B5 - - - G5 - D5 -", "D#5 - - - F#5 - A5 - B5 - - - - - . ."]

# Mission 3, the pylon road: D minor, wide and open, the sun almost through; the gunship in D with a Phrygian Eb.
PYLON = ["D5 - - - A5 - - - F5 - E5 - D5 - - -", "D5 - - . F5 - A#5 - A5 - - - G5 - F5 -",
         "C6 - - - A5 - F5 - A5 - - - C6 - - -", "E5 - - - G5 - C6 - E6 - - - D6 - C6 -",
         "D5 - - - A5 - - - F5 - E5 - D5 - - -", "F5 - - - A#5 - D6 - C6 - A#5 - A5 - - -",
         "G5 - - - A#5 - D6 - A#5 - - - G5 - - -", "C#6 - - - - - A5 - E5 - - - C#5 - . ."]
SPAN = ["F5 - - - - - D5 - A#4 - - - D5 - F5 -", "G5 - - - - - E5 - C5 - - - E5 - G5 -",
        "A5 - - - - - - - F5 - G5 - A5 - - -", "D6 - - - C6 - A5 - F5 - - - - - . .",
        "F5 - - - - - D5 - A#5 - - - A5 - F5 -", "G5 - - - - - C6 - E5 - - - G5 - C6 -",
        "C#6 - - - - - - - A5 - - - E5 - - -", "A5 - - - - - - - - - - - . . . ."]
ROTOR = ["D5 - - - . D5 F5 - E5 - D5 - C5 - A4 -", "D#5 - - - . D#5 G5 - F5 - D#5 - D5 - A#4 -",
         "D5 - - - . D5 A5 - A#5 - - - A5 - F5 -", "C#5 - - - E5 - - - A5 - - - - - . .",
         "D5 - - - . D5 F5 - E5 - D5 - C5 - A4 -", "A#5 - - - A5 - G5 - F5 - - - D#5 - G5 -",
         "F5 - - - A5 - C6 - A5 - - - F5 - C5 -", "C#5 - - - E5 - G5 - A5 - - - - - . ."]

# Mission 4, the Cradle: C minor, the grid's last heartbeat; GRAIVE in C with a Phrygian Db.
CRADLE = ["C5 - - - G5 - - - D#5 - D5 - C5 - - -", "C5 - - . D#5 - G#5 - G5 - - - F5 - D#5 -",
          "A#5 - - - G5 - D#5 - G5 - - - A#5 - - -", "D5 - - - F5 - A#5 - D6 - - - C6 - A#5 -",
          "C5 - - - G5 - - - D#5 - D5 - C5 - - -", "D#5 - - - G#5 - C6 - A#5 - G#5 - G5 - - -",
          "F5 - - - G#5 - C6 - G#5 - - - F5 - - -", "B5 - - - - - G5 - D5 - - - B4 - . ."]
HEART = ["D#5 - - - - - C5 - G#4 - - - C5 - D#5 -", "F5 - - - - - D5 - A#4 - - - D5 - F5 -",
         "G5 - - - - - - - D#5 - F5 - G5 - - -", "C6 - - - A#5 - G5 - D#5 - - - - - . .",
         "D#5 - - - - - C5 - G#5 - - - G5 - D#5 -", "F5 - - - - - A#5 - D5 - - - F5 - A#5 -",
         "B5 - - - - - - - G5 - - - D5 - - -", "G5 - - - - - - - - - - - . . . ."]
CROWN = ["C5 - - - . C5 D#5 - D5 - C5 - A#4 - G4 -", "C#5 - - - . C#5 F5 - D#5 - C#5 - C5 - G#4 -",
         "C5 - - - . C5 G5 - G#5 - - - G5 - D#5 -", "B4 - - - D5 - - - G5 - - - - - . .",
         "C5 - - - . C5 D#5 - D5 - C5 - A#4 - G4 -", "G#5 - - - G5 - F5 - D#5 - - - C#5 - F5 -",
         "D#5 - - - G5 - A#5 - G5 - - - D#5 - A#4 -", "B4 - - - D5 - F5 - G5 - - - - - . ."]

SONGS = {   # bpm, sections: (chords, style, lead: (bars, "lead" or "bell", doubled an octave up) or None)
    "title": (120, [("Am F C G Am F C G", "title", (HOOK, "bell", False))]),
    "stage": (120, [("Am F C G", "intro", None),
                    ("Am F C G Am F C G", "drive", (HOOK, "lead", False)),
                    ("Dm Am F E Dm Am F E", "lift", (LIFT, "lead", False)),
                    ("F G Am", "break", ([HOOK[1], HOOK[3], HOOK[0]], "bell", False)),   # the hook, remembered
                    ("Am", "rise", None),
                    ("Am F C G Am F C E", "drive", (HOOK, "lead", True))]),
    "boss": (140, [("Am Bb Am E Am Bb C E", "boss", None),
                   ("Am Bb Am E Am Bb C E", "boss", (SIEGE, "lead", True))]),
    "line": (128, [("Em C G D", "intro", None),
                   ("Em C G D Em C G B", "drive", (RAIL, "lead", False)),
                   ("C D Em Em C D B B", "lift", (SIGNAL, "lead", False)),
                   ("C D Em", "break", ([RAIL[1], RAIL[3], RAIL[0]], "bell", False)),
                   ("Em", "rise", None),
                   ("Em C G D Em C G B", "drive", (RAIL, "lead", True))]),
    "warden": (146, [("Em F Em B Em F G B", "boss", None),
                     ("Em F Em B Em F G B", "boss", (RAM, "lead", True))]),
    "pylon": (124, [("Dm Bb F C", "intro", None),
                    ("Dm Bb F C Dm Bb Gm A", "drive", (PYLON, "lead", False)),
                    ("Bb C Dm Dm Bb C A A", "lift", (SPAN, "lead", False)),
                    ("Bb C Dm", "break", ([PYLON[1], PYLON[3], PYLON[0]], "bell", False)),
                    ("Dm", "rise", None),
                    ("Dm Bb F C Dm Bb Gm A", "drive", (PYLON, "lead", True))]),
    "harrow": (150, [("Dm Eb Dm A Dm Eb F A", "boss", None),
                     ("Dm Eb Dm A Dm Eb F A", "boss", (ROTOR, "lead", True))]),
    "cradle": (126, [("Cm Ab Eb Bb", "intro", None),
                     ("Cm Ab Eb Bb Cm Ab Fm G", "drive", (CRADLE, "lead", False)),
                     ("Ab Bb Cm Cm Ab Bb G G", "lift", (HEART, "lead", False)),
                     ("Ab Bb Cm", "break", ([CRADLE[1], CRADLE[3], CRADLE[0]], "bell", False)),
                     ("Cm", "rise", None),
                     ("Cm Ab Eb Bb Cm Ab Fm G", "drive", (CRADLE, "lead", True))]),
    "graive": (154, [("Cm Db Cm G Cm Db Eb G", "boss", None),
                     ("Cm Db Cm G Cm Db Eb G", "boss", (CROWN, "lead", True))]),
}
CHUNK = 512                 # samples between yields


def midi(name):
    return NOTE[name[:-1]] + 12 * (int(name[-1]) + 1)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _zeros(n):
    return array("f", bytes(4 * n))


def _blep(p, dt):
    """PolyBLEP: rounds a saw or square edge over one sample, so its harmonics stop folding back as
    metallic noise (aliasing) at this low sample rate."""
    if p < dt:
        p /= dt
        return p + p - p * p - 1
    if p > 1 - dt:
        p = (p - 1) / dt
        return p * p + p + p + 1
    return 0.0


def _lp(fc):
    """One-pole low-pass coefficient for a cutoff in Hz."""
    return 1 - math.exp(-2 * math.pi * fc / RATE)


def _add(dst, src, at, gain=1.0):
    n = min(len(src), len(dst) - at)
    for i in range(n):
        if i % CHUNK == 0:
            yield
        dst[at + i] += src[i] * gain


# ------------------------------------------------------------------ drums (rendered once)

_kit = None


def _drums():
    global _kit
    if _kit is None:
        _kit = _make_drums()
    return _kit


def _make_drums():
    rnd = random.Random(7)
    noise = [rnd.uniform(-1, 1) for _ in range(int(1.6 * RATE))]

    def kick():
        out, ph = _zeros(int(0.3 * RATE)), 0.0
        for i in range(len(out)):
            t = i / RATE
            ph += (45 + 110 * math.exp(-t / 0.035)) / RATE
            v = math.sin(2 * math.pi * ph) * math.exp(-t / 0.18) + noise[i] * 0.08 * math.exp(-t / 0.002)
            out[i] = math.tanh(1.6 * v) * 0.6
        return out

    def snare():
        body, lo, hi = _zeros(int(0.25 * RATE)), 0.0, 0.0
        for i in range(len(body)):
            t = i / RATE
            lo += _lp(2800) * (noise[i] - lo)
            hi += _lp(700) * (lo - hi)                    # band-passed noise: the snare wires
            body[i] = math.sin(2 * math.pi * 185 * t) * 0.6 * math.exp(-t / 0.06) + (lo - hi) * 0.75 * math.exp(-t / 0.06)
        tails = []                                        # the 80s gated reverb, a different noise per side
        for off in (3000, 9000):
            tail, lo = _zeros(int(0.2 * RATE)), 0.0
            for i in range(len(tail)):
                t = i / RATE
                lo += _lp(2200) * (noise[i + off] - lo)
                gate = min(1.0, max(0.0, (0.18 - t) / 0.012)) * min(1.0, t / 0.01)
                tail[i] = lo * 0.2 * math.exp(-t / 0.3) * gate
            tails.append(tail)
        return body, tails

    def hat(seconds, decay, vol, off, fc=6000):
        out, lo = _zeros(int(seconds * RATE)), 0.0
        for i in range(len(out)):
            x = noise[i + off]
            lo += _lp(fc) * (x - lo)
            out[i] = (x - lo) * vol * math.exp(-i / RATE / decay) * min(1.0, i / 25)
        return out

    def crash(off):
        out, lo = _zeros(int(1.4 * RATE)), 0.0
        for i in range(len(out)):
            x = noise[(i + off) % len(noise)]
            lo += _lp(3000) * (x - lo)
            out[i] = (x - lo) * 0.3 * math.exp(-i / RATE / 0.45) * min(1.0, i / 30)
        return out

    def fade(out):                                        # every hit ends at zero: a cut-off tail clicks
        k = min(len(out), 200)
        for i in range(k):
            out[len(out) - k + i] *= 1 - (i + 1) / k
        return out

    sn, tails = snare()
    kit = {"kick": kick(), "snare": sn, "tails": tails, "hat": hat(0.03, 0.008, 0.16, 100),
            "ohat": hat(0.16, 0.05, 0.11, 2000, fc=3500), "crash": (crash(0), crash(11000))}
    for v in kit.values():
        for out in (v if isinstance(v, (tuple, list)) else (v,)):
            fade(out)
    return kit


PATTERNS = {   # drums: kicks, snares, open hats (16th steps), closed hats every n steps (0: none)
    "full": ((0, 4, 8, 12), (4, 12), (2, 6, 10, 14), 0),
    "half": ((0, 8), (), (6, 14), 0),
    "boss": ((0, 3, 6, 8, 11, 14), (4, 12), (2, 6, 10, 14), 0),
    "rise": ((), (), (), 0),
    "none": ((), (), (), 0),
}


# ------------------------------------------------------------------ one bar of backing

def _bed(chord, style, per, kit):
    drums, bass_n, pad_fc, arp = STYLES[style]
    kicks, snares, ohats, hat_every = PATTERNS[drums]
    n = 16 * per
    L, R, S = _zeros(n), _zeros(n), _zeros(n)
    root, iv = CHORDS[chord]

    duck = [1.0] * n                                      # side-chain: everything else dips under the kick
    for k in kicks:
        for i in range(k * per, n):
            if i % CHUNK == 0:
                yield
            duck[i] = min(duck[i], 1 - 0.6 * math.exp(-(i - k * per) / (0.08 * RATE)))

    # pad: four chord tones, two detuned saws each, one per side, through a low-pass
    tones = [hz(root + x) for x in iv] + [hz(root + 12)]
    a = _lp(pad_fc)
    for side, det, out in ((0, -0.1, L), (1, 0.1, R)):
        incs = [f * 2 ** (det / 12) / RATE for f in tones]
        phs = [(0.31 * j + 0.5 * side) % 1 for j in range(4)]
        y1 = y2 = 0.0
        for i in range(n):
            if i % CHUNK == 0:
                yield
            s = 0.0
            for j in range(4):
                p = (phs[j] + incs[j]) % 1.0
                phs[j] = p
                s += 2 * p - 1 - _blep(p, incs[j])
            y1 += a * (s - y1)
            y2 += a * (y1 - y2)
            env = min(1.0, i / (0.05 * RATE), (n - i) / (0.02 * RATE))
            out[i] += y2 * 0.045 * env * duck[i]

    # bass: a saw on the 8ths, root then octave, each note a soft filter pluck
    if bass_n:
        b = hz((root % 12) + 36)
        step = 16 // bass_n
        for s in range(0, 16, step):
            yield
            f = b * (2 if s % 4 == 2 else 1)
            ph, y = 0.0, 0.0
            m = int(per * step * 0.85)
            for i in range(m):
                if i % CHUNK == 0:
                    yield
                t = i / RATE
                ph = (ph + f / RATE) % 1.0
                y += _lp(160 + 650 * math.exp(-t / 0.08)) * ((2 * ph - 1 - _blep(ph, f / RATE)) - y)
                j = s * per + i
                v = y * 0.32 * min(1.0, i / 40, (m - i) / 60) * duck[j]
                L[j] += v
                R[j] += v

    # arpeggio: a soft triangle up and down the chord, two octaves up, alternating sides, into the delay
    if arp:
        notes = [hz(root + 12 + x) for x in iv] + [hz(root + 24)]
        order = (0, 1, 2, 3, 2, 1, 2, 3)
        for s in range(16):
            yield
            f, ph = notes[order[s % 8]], 0.0
            pan = 0.45 if s % 2 else -0.45
            for i in range(per):
                if i % CHUNK == 0:
                    yield
                ph = (ph + f / RATE) % 1.0
                v = (4 * abs(ph - 0.5) - 1) * 0.05 * math.exp(-i / (0.12 * RATE)) * min(1.0, i / 150, (per - i) / 200)
                v *= 0.6 + 0.4 * duck[s * per + i]
                j = s * per + i
                L[j] += v * (1 - pan)
                R[j] += v * (1 + pan)
                S[j] += v * 0.3

    # drums
    for k in kicks:
        yield from _add(L, kit["kick"], k * per)
        yield from _add(R, kit["kick"], k * per)
    for sn in snares:
        yield from _add(L, kit["snare"], sn * per, 0.9)
        yield from _add(R, kit["snare"], sn * per, 0.9)
        yield from _add(L, kit["tails"][0], sn * per)
        yield from _add(R, kit["tails"][1], sn * per)
    for s in ohats:
        yield from _add(L, kit["ohat"], s * per, 0.7)
        yield from _add(R, kit["ohat"], s * per, 1.0)
    for s in range(0, 16, hat_every) if hat_every else ():
        if s not in ohats:
            yield from _add(L, kit["hat"], s * per, 0.7)
            yield from _add(R, kit["hat"], s * per)
    if drums == "rise":                                   # snare roll and a noise sweep into the drop
        for s in range(16):
            g = 0.15 + 0.75 * s / 15
            yield from _add(L, kit["snare"], s * per, g * 0.7)
            yield from _add(R, kit["snare"], s * per, g * 0.7)
        rnd, yl, yr = random.Random(3), 0.0, 0.0
        for i in range(n):
            if i % CHUNK == 0:
                yield
            x = i / n
            c = _lp(300 + 6000 * x * x)
            yl += c * (rnd.uniform(-1, 1) - yl)
            yr += c * (rnd.uniform(-1, 1) - yr)
            L[i] += yl * 0.35 * x
            R[i] += yr * 0.35 * x
    return L, R, S


# ------------------------------------------------------------------ the lead

def _lead(bars, at, per, L, R, S, up=0, vol=0.11, pan=0.0, t0=0, bell=False):
    tokens = []
    for bar in bars:
        bar = bar.split()
        assert len(bar) == 16, bar                        # every bar is sixteen 16ths
        tokens += bar
    notes, prev = [], None                                # (start step, length, midi, glide from)
    for s, tok in enumerate(tokens):
        if tok == "-" and notes:
            notes[-1][1] += 1
        elif tok == ".":
            prev = None
        elif tok != "-":
            m = midi(tok) + up
            notes.append([s, 1, m, prev])
            prev = m
    a = _lp(2800)
    for s, length, m, frm in notes:
        n = length * per
        f1 = hz(m)
        f0 = hz(frm) if frm is not None else f1
        ph1 = ph2 = y1 = y2 = 0.0
        for i in range(n):
            if i % CHUNK == 0:
                yield
            t = i / RATE
            if bell:                                      # two-operator FM: a bright strike that melts away
                ph1 = (ph1 + f1 / RATE) % 1.0
                v = math.sin(2 * math.pi * ph1 + 1.2 * math.exp(-t / 0.15) * math.sin(6 * math.pi * ph1))
                v *= vol * 1.3 * math.exp(-t / 0.5) * min(1.0, i / 120, (n - i) / 200)
                j = at + s * per + i
                L[j] += v * (1 - pan)
                R[j] += v * (1 + pan)
                S[j] += v * 0.8
                continue
            g = min(1.0, t / 0.04)                        # glide from the note before when legato
            vib = 1 + 0.009 * min(1.0, max(0.0, (t - 0.18) / 0.25)) * math.sin(2 * math.pi * 5.5 * t)
            f = (f0 + (f1 - f0) * g) * vib
            ph1 = (ph1 + f / RATE) % 1.0
            ph2 = (ph2 + f * 1.007 / RATE) % 1.0
            duty = 0.5 + 0.22 * math.sin(2 * math.pi * 0.6 * (t0 + s * per + i) / RATE)   # slow PWM
            d1, d2 = f / RATE, f * 1.007 / RATE
            sq = (1.0 if ph1 < duty else -1.0) + _blep(ph1, d1) - _blep((ph1 - duty) % 1.0, d1)
            x = sq * 0.55 + (2 * ph2 - 1 - _blep(ph2, d2)) * 0.45
            y1 += a * (x - y1)
            y2 += a * (y1 - y2)
            env = min(1.0, i / 120 if frm is None else 1.0, (n - i) / 300)
            v = y2 * vol * env
            j = at + s * per + i
            L[j] += v * (1 - pan)
            R[j] += v * (1 + pan)
            S[j] += v * 0.5


# ------------------------------------------------------------------ the song

def render(name):
    """The whole song at once (desktop thread, tests, tools)."""
    gen = build(name)
    while True:
        try:
            next(gen)
        except StopIteration as done:
            return done.value


def build(name):
    bpm, sections = SONGS[name]
    per = int(RATE * 60 / bpm / 4)
    bar = 16 * per
    total = sum(len(c.split()) for c, *_ in sections) * bar
    L, R, S = _zeros(total), _zeros(total), _zeros(total)
    kit, beds, at = _drums(), {}, 0
    for chords, style, _ in sections:                      # backings first: plain copies, the bars never overlap
        for chord in chords.split():
            if (chord, style) not in beds:
                beds[chord, style] = yield from _bed(chord, style, per, kit)
            for dst, src in zip((L, R, S), beds[chord, style]):
                dst[at:at + bar] = src
            at += bar
    at = 0
    for chords, style, lead in sections:
        if style not in ("intro", "title"):
            yield from _add(L, kit["crash"][0], at)
            yield from _add(R, kit["crash"][1], at)
        if lead:
            bars, timbre, double = lead
            yield from _lead(bars, at, per, L, R, S, t0=at, bell=timbre == "bell")
            if double:
                yield from _lead(bars, at, per, L, R, S, up=12, vol=0.035, pan=0.3, t0=at)
        at += len(chords.split()) * bar

    # ping-pong delay on a dotted 8th, darker on every repeat
    d, fb, a = 3 * per, 0.45, _lp(2500)
    el, er, zl, zr = _zeros(total), _zeros(total), 0.0, 0.0
    peak = 1e-9
    for j in range(total):
        if j % CHUNK == 0:
            yield
        x = S[j - d] + fb * er[j - d]
        zl += a * (x - zl)
        el[j] = zl
        zr += a * (fb * el[j - d] - zr)
        er[j] = zr
        L[j] += zl * 0.5
        R[j] += zr * 0.5
        peak = max(peak, abs(L[j]), abs(R[j]))

    k, norm = 1.2 / peak, 0.9 * 32767 / math.tanh(1.2)    # soft clip, peak at 90 % of full scale
    out = array("h", bytes(4 * total))
    for c in range(0, total, CHUNK):
        yield
        e = min(total, c + CHUNK)
        out[2 * c:2 * e:2] = array("h", (int(math.tanh(v * k) * norm) for v in L[c:e]))
        out[2 * c + 1:2 * e:2] = array("h", (int(math.tanh(v * k) * norm) for v in R[c:e]))
    return out

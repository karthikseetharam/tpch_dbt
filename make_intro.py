"""15-second cricket team intro: upbeat Indian groove (dhol, tabla, sitar),
drums, piano, and chant vocals. Pure Python (no numpy needed).

Usage: python make_intro.py <vox_dir> <out.wav>
"""
import math, random, struct, sys, wave

SR = 44100
BPM = 128
BEAT = 60 / BPM            # 0.46875 s
BAR = BEAT * 4             # 1.875 s  -> 8 bars = 15 s
STEP = BEAT / 4            # 16th note
DUR = 15.0
N = int(SR * DUR)
L = [0.0] * N
R = [0.0] * N
random.seed(7)
TWO_PI = 2 * math.pi


def t_at(bar, step=0):
    return bar * BAR + step * STEP


def add(samples, start_t, gain=1.0, pan=0.0):
    """Mix mono samples in at start_t seconds, pan -1 (L) .. +1 (R)."""
    s0 = int(start_t * SR)
    gl = gain * math.cos((pan + 1) * math.pi / 4) * 1.414
    gr = gain * math.sin((pan + 1) * math.pi / 4) * 1.414
    for i, v in enumerate(samples):
        j = s0 + i
        if j >= N:
            break
        if j >= 0:
            L[j] += v * gl
            R[j] += v * gr


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def highpass(x, a=0.85):
    out, prev_x, prev_y = [], 0.0, 0.0
    for v in x:
        y = a * (prev_y + v - prev_x)
        out.append(y)
        prev_x, prev_y = v, y
    return out


# ---------------------------------------------------------------- instruments
def dhol_bass(vel=1.0):
    n = int(0.42 * SR); out = []; ph = 0.0
    for i in range(n):
        t = i / SR
        f = 58 + 75 * math.exp(-t * 28)
        ph += TWO_PI * f / SR
        v = math.sin(ph) * math.exp(-t * 7.5)
        v += 0.35 * math.sin(2 * ph) * math.exp(-t * 14)
        if i < 220:
            v += (random.random() * 2 - 1) * 0.5 * (1 - i / 220)  # skin slap
        out.append(math.tanh(v * 1.6) * vel)
    return out


def dhol_tilli(vel=1.0):
    n = int(0.11 * SR)
    noise = highpass([random.random() * 2 - 1 for _ in range(n)], 0.7)
    out = []
    for i in range(n):
        t = i / SR
        v = noise[i] * math.exp(-t * 55) * 0.8
        v += math.sin(TWO_PI * 430 * t) * math.exp(-t * 40) * 0.6
        out.append(v * vel)
    return out


def tabla_na(vel=1.0, f=690):
    n = int(0.3 * SR); out = []
    for i in range(n):
        t = i / SR
        bend = 1 + 0.03 * math.exp(-t * 40)
        v = (math.sin(TWO_PI * f * bend * t) + 0.5 * math.sin(TWO_PI * 2 * f * bend * t)
             + 0.25 * math.sin(TWO_PI * 3.01 * f * t)) * math.exp(-t * 16)
        if i < 120:
            v += (random.random() * 2 - 1) * 0.4
        out.append(v * 0.5 * vel)
    return out


def clap(vel=1.0):
    n = int(0.2 * SR)
    noise = highpass([random.random() * 2 - 1 for _ in range(n)], 0.6)
    out = []
    for i in range(n):
        t = i / SR
        env = math.exp(-t * 22)
        for off in (0.0, 0.009, 0.018):  # flammed attacks
            if t >= off:
                env += 0.6 * math.exp(-(t - off) * 180)
        out.append(noise[i] * env * 0.5 * vel)
    return out


def shaker(vel=1.0):
    n = int(0.06 * SR)
    noise = highpass(highpass([random.random() * 2 - 1 for _ in range(n)], 0.5), 0.5)
    return [noise[i] * math.exp(-i / SR * 70) * vel * 0.35 for i in range(n)]


def crash(length=2.4):
    n = int(length * SR)
    noise = highpass(highpass([random.random() * 2 - 1 for _ in range(n)], 0.55), 0.6)
    return [noise[i] * math.exp(-i / SR * 2.2) * 0.55 for i in range(n)]


def riser(length):
    n = int(length * SR)
    noise = highpass([random.random() * 2 - 1 for _ in range(n)], 0.8)
    return [noise[i] * (i / n) ** 2.5 * 0.35 for i in range(n)]


def piano(note, length=1.1, vel=1.0):
    f = midi(note); n = int(length * SR); out = []
    parts = [(k, 1 / k ** 1.25, 1.4 + 0.9 * k, 1 + 0.0004 * k * k) for k in range(1, 8)]
    for i in range(n):
        t = i / SR
        v = 0.0
        for k, amp, dec, st in parts:
            v += amp * math.sin(TWO_PI * k * st * f * t) * math.exp(-t * dec)
        att = min(1.0, i / 90)
        rel = min(1.0, (n - i) / 600)
        out.append(v * att * rel * 0.22 * vel)
    return out


def sitar(note, length=0.5, vel=1.0, bend=0.0):
    """Karplus-Strong pluck with a buzzy 'jawari' bridge and optional meend."""
    f = midi(note)
    period = SR / f
    buf_len = int(period) + 2
    buf = [random.random() * 2 - 1 for _ in range(buf_len)]
    n = int(length * SR); out = []
    idx = 0.0; prev = 0.0
    for i in range(n):
        t = i / SR
        cur_period = period / (2 ** (bend * min(1.0, t / 0.12) / 12))
        p = int(idx) % buf_len
        q = (p + 1) % buf_len
        v = 0.5 * (buf[p] + buf[q]) * 0.996
        buf[p] = v
        idx += period / cur_period
        buzz = math.tanh(v * 3.0) * 0.6 + v * 0.4
        y = buzz - prev * 0.3
        prev = buzz
        out.append(y * vel * 0.45 * min(1.0, (n - i) / 400))
        if idx >= buf_len:
            idx -= buf_len
    return out


def bass(note, length=0.35, vel=1.0):
    f = midi(note); n = int(length * SR)
    return [(math.sin(TWO_PI * f * i / SR) + 0.3 * math.sin(TWO_PI * 2 * f * i / SR))
            * math.exp(-i / SR * 3) * min(1, (n - i) / 400) * 0.5 * vel for i in range(n)]


def drone():
    out = []
    for i in range(N):
        t = i / SR
        v = 0.0
        for note, a in ((50, 1.0), (57, 0.6), (62, 0.5)):  # D3, A3, D4
            f = midi(note)
            for k in (1, 2, 3, 4):
                v += a / k * math.sin(TWO_PI * k * f * t * (1 + 0.0007 * k) + k)
        swell = 0.6 + 0.4 * math.sin(TWO_PI * 0.5 * t)
        fade = min(1.0, t / 1.5) * min(1.0, (DUR - t) / 1.5)
        out.append(v * 0.025 * swell * fade)
    return out


def load_vox(path):
    with wave.open(path) as w:
        raw = w.readframes(w.getnframes())
    x = [s / 32768 for s in struct.unpack('<%dh' % (len(raw) // 2), raw)]
    thr = 0.02
    a = next(i for i, v in enumerate(x) if abs(v) > thr)
    b = len(x) - next(i for i, v in enumerate(reversed(x)) if abs(v) > thr)
    x = x[max(0, a - 200):b + 2000]
    pk = max(abs(v) for v in x) or 1
    return [math.tanh(v / pk * 2.2) / math.tanh(2.2) for v in x]  # punchy


# ---------------------------------------------------------------- arrangement
D, C, G, A, E, Fs, B = 62, 60, 67, 69, 64, 66, 71
CHORDS = {  # bar -> list of (start_step, chord notes, root)
    0: [(0, [50, 57, 62, 66], 38)],
    1: [(0, [50, 57, 62, 66], 38)],
    2: [(0, [62, 66, 69], 38)],
    3: [(0, [60, 64, 67], 36)],
    4: [(0, [59, 62, 67], 43)],
    5: [(0, [61, 64, 69], 45)],
    6: [(0, [59, 62, 67], 43), (8, [61, 64, 69], 45)],
    7: [(0, [62, 66, 69, 74], 38)],
}


def chord_at(bar, step):
    cur = CHORDS[bar][0]
    for c in CHORDS[bar]:
        if c[0] <= step:
            cur = c
    return cur


print('drums...')
BASS_STEPS = [0, 6, 8, 14]          # bhangra-style chaal
TILLI_STEPS = [3, 4, 7, 11, 12, 15]
db = dhol_bass(); dt = dhol_tilli(); na = tabla_na(); na_hi = tabla_na(0.8, 820)
cl = clap(); sh = shaker()

# Bar 0: light tabla + shaker intro
for s in (0, 3, 6, 8, 10, 12, 14):
    add(na if s % 4 else na_hi, t_at(0, s), 0.7, 0.3)
for s in range(16):
    add(sh, t_at(0, s), 0.6 if s % 2 else 0.3, -0.4)
# Bar 1: dhol roll crescendo
for s in range(16):
    v = 0.3 + 0.7 * s / 15
    add(dt, t_at(1, s), v, 0.15)
    if s % 4 == 0:
        add(db, t_at(1, s), v * 0.8)
add(riser(BAR), t_at(1), 0.8)

# Bars 2-5 full groove, bar 6 groove + roll
for bar in range(2, 7):
    for s in BASS_STEPS:
        add(db, t_at(bar, s), 1.0)
    for s in TILLI_STEPS:
        add(dt, t_at(bar, s), 0.8, 0.15)
    for s in (4, 12):
        add(cl, t_at(bar, s), 0.9)
    for s in range(16):
        add(sh, t_at(bar, s), 0.7 if s % 2 else 0.35, -0.4)
    for s in (2, 10):
        add(na, t_at(bar, s), 0.5, 0.4)
    if bar == 6:
        for s in range(8, 16):
            add(dt, t_at(bar, s), 0.6 + 0.05 * s, -0.15)
            add(db, t_at(bar, s), 0.5 + 0.04 * s)
add(crash(), t_at(2), 0.7, -0.2)
add(riser(BAR), t_at(6), 1.0)

# Bar 7: final big hit
add(db, t_at(7), 1.3); add(dt, t_at(7), 1.0); add(cl, t_at(7), 1.0)
add(crash(1.875), t_at(7), 0.9, 0.2)
add(db, t_at(7, 3), 0.9); add(db, t_at(7, 4), 1.1)
add(dt, t_at(7, 3), 0.8); add(cl, t_at(7, 4), 0.8)

print('piano + bass...')
STAB = [0, 3, 6, 10, 12]
for bar in range(2, 7):
    for s in STAB:
        _, notes, root = chord_at(bar, s)
        for nt in notes:
            add(piano(nt, 0.5, 0.9 if s == 0 else 0.7), t_at(bar, s), 1.0, 0.25)
    for s in BASS_STEPS:
        _, _, root = chord_at(bar, s)
        add(bass(root, 0.3), t_at(bar, s), 0.9)
# Intro piano: sustained chord in bar 0, pulsing 8ths in bar 1
for nt in CHORDS[0][0][1]:
    add(piano(nt, 1.9, 0.7), t_at(0), 1.0, 0.25)
for s in range(0, 16, 2):
    for nt in (62, 66, 69):
        add(piano(nt, 0.25, 0.4 + 0.5 * s / 16), t_at(1, s), 1.0, 0.25)
# Bar 6: rising piano run (D Khamaj scale) over the build
run = [62, 64, 66, 67, 69, 71, 72, 74, 76, 78, 79, 81, 83, 84, 86, 88]
for s, nt in enumerate(run):
    add(piano(nt, 0.3, 0.6), t_at(6, s), 1.0, 0.3)
# Final chord ring-out
for nt in [38, 50, 57, 62, 66, 69, 74, 78]:
    add(piano(nt, 1.85, 1.0), t_at(7), 1.0, 0.25)
add(bass(38, 1.8), t_at(7), 1.0)

print('sitar...')
# Intro hook (eighth notes), Khamaj flavour with flat-7 (C)
hook0 = [(0, A, 0.5), (2, G, 0), (4, Fs, 0), (6, E, 0), (8, Fs, 0), (10, E, 0), (12, D, 0), (14, C, 0)]
hook1 = [(0, D, 0), (2, E, 0), (4, Fs, 0), (6, G, 0), (8, A, 0), (10, B, 0), (12, 72, 0), (14, 74, 2)]
for s, nt, bend in hook0:
    add(sitar(nt, 0.45, 1.0, bend), t_at(0, s), 1.0, -0.3)
for s, nt, bend in hook1:
    add(sitar(nt, 0.45, 1.0, bend), t_at(1, s), 1.0, -0.3)
# Answer fills in the vocal gaps (end of bars 3 and 5)
fill = [(12, 74), (13, 72), (14, 69), (15, 67)]
for bar in (3, 5):
    for s, nt in fill:
        add(sitar(nt, 0.3, 0.8), t_at(bar, s), 0.9, -0.4)
# Final sitar flourish
for k, nt in enumerate([69, 72, 74]):
    add(sitar(nt, 0.6 if k == 2 else 0.2, 1.0, 0.0), t_at(7, 8 + 2 * k), 0.9, -0.3)

print('drone...')
add(drone(), 0.0, 1.0)

print('vocals...')
vox_dir = sys.argv[1]
V = {}
for k in ('rock', 'roar', 'win', 'hey'):
    V[k] = (load_vox(f'{vox_dir}/{k}_m.wav'), load_vox(f'{vox_dir}/{k}_f.wav'))


def chant(key, t, gain=1.0):
    m, f = V[key]
    add(m, t, 0.55 * gain, -0.35)
    add(f, t + 0.012, 0.45 * gain, 0.35)
    add(m, t + 0.025, 0.2 * gain, 0.6)          # doubling
    add(f, t + BEAT / 2, 0.12 * gain, -0.6)     # 8th-note echo
    add(m, t + BEAT / 2, 0.12 * gain, 0.6)


for bar in (2, 4):
    chant('rock', t_at(bar, 0))
    chant('roar', t_at(bar, 8))
    chant('win', t_at(bar + 1, 0), 1.1)
chant('hey', t_at(6, 0), 0.9)
chant('hey', t_at(6, 8), 1.0)
chant('win', t_at(7, 0) + 0.05, 1.2)

print('mix...')
fade_n = int(0.4 * SR)
peak = max(max(abs(v) for v in L), max(abs(v) for v in R))
g = 1.6 / peak
frames = bytearray()
for i in range(N):
    fo = min(1.0, (N - i) / fade_n)
    l = math.tanh(L[i] * g) * 0.93 * fo
    r = math.tanh(R[i] * g) * 0.93 * fo
    frames += struct.pack('<hh', int(l * 32767), int(r * 32767))
with wave.open(sys.argv[2], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(bytes(frames))
print('done', sys.argv[2])

"""Game sound-effect generators. Each takes (sr, **params) and returns a mono buffer."""
from __future__ import annotations

import numpy as np

from . import filters as F
from . import osc as O
from .core import DEFAULT_SR, mix, samples
from .env import adsr, apply, perc, lfo
from .notes import to_hz

REGISTRY: dict[str, dict] = {}


def sfx(name: str, desc: str, **params):
    def deco(fn):
        REGISTRY[name] = {"fn": fn, "desc": desc, "params": params}
        return fn
    return deco


def _dec(n, tau, sr):
    return np.exp(-np.arange(n) / (tau * sr))


@sfx("beep", "Simple UI beep.", freq=(880, "Hz or note name (110, '110hz' or 'A2')"), dur=(0.12, "s"), wave=("sine", "sine|square|triangle|saw|pulse"))
def beep(sr=DEFAULT_SR, freq=880, dur=0.12, wave="sine"):
    f = to_hz(freq)
    n = samples(dur + 0.02, sr)
    x = O.osc(wave, f, n, sr, width=0.3)
    if wave != "sine":
        x = F.lowpass(x, min(f * 8, 12000), sr) * 0.6
    return apply(x, adsr(dur, 0.004, 0.0, 1.0, 0.02, sr)) * 0.8


@sfx("blip", "Very short high blip (cursor move, tick).", freq=(1400, "Hz or note name (110, '110hz' or 'A2')"), dur=(0.05, "s"))
def blip(sr=DEFAULT_SR, freq=1400, dur=0.05):
    f = to_hz(freq)
    n = samples(dur, sr)
    return O.square(f, n, sr) * perc(dur, 0.001, sr, curve=1.5) * 0.4


@sfx("click", "Mechanical click / tick.", tone=(3000, "Hz"))
def click(sr=DEFAULT_SR, tone=3000):
    n = samples(0.03, sr)
    x = F.bandpass(O.white(n, seed=21), tone, sr, 1.5) * _dec(n, 0.003, sr)
    x += O.sine(tone / 2, n, sr) * _dec(n, 0.002, sr) * 0.5
    return x * 1.5


@sfx("pop", "Soft bubble pop.", freq=(500, "Hz"))
def pop(sr=DEFAULT_SR, freq=500):
    n = samples(0.08, sr)
    f = freq * (1 + 2 * _dec(n, 0.01, sr))
    return O.sine(f, n, sr) * _dec(n, 0.02, sr) * perc(0.08, 0.0005, sr, curve=1.0) * 0.9


@sfx("coin", "Classic coin / pickup: two quick rising notes.", freq=("B5", "first note or Hz"), up=(5, "semitones jump"), wave=("square", "square|sine|triangle"))
def coin(sr=DEFAULT_SR, freq="B5", up=5, wave="square"):
    f1 = to_hz(freq)
    f2 = f1 * 2 ** (up / 12)
    n1 = samples(0.08, sr)
    n2 = samples(0.35, sr)
    a = O.osc(wave, f1, n1, sr) * 0.5
    b = O.osc(wave, f2, n2, sr) * 0.5 * adsr(0.15, 0.002, 0.1, 0.5, 0.2, sr)[:n2]
    y = np.concatenate([a, b])
    return F.lowpass(y, 9000, sr) * 0.8


@sfx("powerup", "Rising arpeggio power-up.", freq=("C5", "start note or Hz"), steps=(6, "count"), step=(3, "semitones per step"),
     rate=(0.05, "s per step"), wave=("square", "square|saw|sine"))
def powerup(sr=DEFAULT_SR, freq="C5", steps=6, step=3, rate=0.05, wave="square"):
    f0 = to_hz(freq)
    parts = []
    for i in range(int(steps)):
        f = f0 * 2 ** (i * step / 12)
        d = rate if i < steps - 1 else rate * 5
        n = samples(d, sr)
        x = O.osc(wave, f, n, sr) * 0.45 * adsr(d, 0.002, 0.0, 1.0, 0.0, sr)[:n]
        if i == steps - 1:
            x *= _dec(n, d / 3, sr)
        parts.append((x, i * rate))
    return F.lowpass(mix(parts, sr), 8000, sr)


@sfx("powerdown", "Falling arpeggio power-down / lose life.", freq=("C6", "start note or Hz"), steps=(6, "count"), rate=(0.07, "s per step"))
def powerdown(sr=DEFAULT_SR, freq="C6", steps=6, rate=0.07):
    f0 = to_hz(freq)
    parts = []
    for i in range(int(steps)):
        f = f0 * 2 ** (-i * 3 / 12)
        n = samples(rate * (1 if i < steps - 1 else 4), sr)
        x = O.square(f, n, sr) * 0.4 * _dec(n, rate * 2, sr)
        parts.append((x, i * rate))
    return F.lowpass(mix(parts, sr), 6000, sr)


@sfx("laser", "Descending laser / pew.", start=(2400, "Hz"), end=(300, "Hz"), dur=(0.25, "s"), wave=("saw", "saw|square|sine"))
def laser(sr=DEFAULT_SR, start=2400, end=300, dur=0.25, wave="saw"):
    f = O.sweep(start, end, dur, sr)
    n = f.shape[0]
    x = O.osc(wave, f, n, sr)
    x = F.lowpass(x, 8000, sr) * perc(dur, 0.002, sr, curve=1.5)
    return x * 0.6


@sfx("zap", "Electric zap / shock (noisy, buzzy).", dur=(0.2, "s"), freq=(120, "buzz Hz"))
def zap(sr=DEFAULT_SR, dur=0.2, freq=120):
    n = samples(dur, sr)
    f = freq * (1 + 6 * _dec(n, 0.03, sr))
    x = O.saw(f, n, sr) * O.white(n, seed=22) * 1.5
    x = F.bandpass(x, 1500, sr, 0.5)
    return np.tanh(x * 3) * perc(dur, 0.001, sr, curve=2.0) * 0.8


@sfx("hit", "Impact / hurt hit (noise burst + pitch drop).", dur=(0.25, "s"), tone=(200, "Hz"), crunch=(0.5, "0..1 distortion"))
def hit(sr=DEFAULT_SR, dur=0.25, tone=200, crunch=0.5):
    n = samples(dur, sr)
    f = tone * (1 + 3 * _dec(n, 0.02, sr))
    body = O.square(f, n, sr) * _dec(n, dur / 4, sr)
    nz = F.lowpass(O.white(n, seed=23), 3000, sr) * _dec(n, dur / 5, sr)
    y = np.tanh((body + nz) * (1 + 4 * crunch))
    return y * perc(dur, 0.001, sr, curve=1.0) * 0.8


@sfx("punch", "Meaty punch / body hit.", dur=(0.2, "s"))
def punch(sr=DEFAULT_SR, dur=0.2):
    n = samples(dur, sr)
    f = 80 * (1 + 5 * _dec(n, 0.02, sr))
    y = O.sine(f, n, sr) * _dec(n, dur / 4, sr)
    y += F.bandpass(O.brown(n, seed=24), 400, sr, 0.7) * _dec(n, 0.05, sr) * 1.2
    return np.tanh(y * 2.5) * perc(dur, 0.001, sr, curve=1.0) * 0.9


@sfx("explosion", "Explosion: brown noise with falling lowpass.", dur=(1.2, "s"), boom=(1.0, "low rumble amount"))
def explosion(sr=DEFAULT_SR, dur=1.2, boom=1.0):
    n = samples(dur, sr)
    nz = O.brown(n, seed=25) * 0.7 + O.white(n, seed=26) * 0.3
    fc = 200 + 6000 * _dec(n, dur / 6, sr)
    y = F.biquad(nz, "lowpass", fc, sr, q=0.9)
    rumble = O.sine(45 * (1 + 2 * _dec(n, 0.05, sr)), n, sr) * _dec(n, dur / 3, sr) * boom
    y = np.tanh((y * 2.0 + rumble) * 1.5)
    return y * perc(dur, 0.005, sr, curve=1.8)


@sfx("jump", "Platformer jump (rising sweep).", start=(300, "Hz"), end=(900, "Hz"), dur=(0.18, "s"))
def jump(sr=DEFAULT_SR, start=300, end=900, dur=0.18):
    f = O.sweep(start, end, dur, sr)
    n = f.shape[0]
    x = O.square(f, n, sr)
    return F.lowpass(x, 6000, sr) * adsr(dur - 0.03, 0.005, 0.0, 1.0, 0.03, sr)[:n] * 0.45


@sfx("whoosh", "Air whoosh / swipe (filtered noise sweep).", dur=(0.5, "s"), low=(300, "Hz"), high=(4000, "Hz"), direction=("up", "up|down"))
def whoosh(sr=DEFAULT_SR, dur=0.5, low=300, high=4000, direction="up"):
    n = samples(dur, sr)
    fc = O.sweep(low, high, dur, sr) if direction == "up" else O.sweep(high, low, dur, sr)
    y = F.biquad(O.white(n, seed=27), "bandpass", fc, sr, q=1.2)
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    return y * env * 1.5


@sfx("swoosh", "Faster, sharper swipe for UI page transitions.", dur=(0.25, "s"))
def swoosh(sr=DEFAULT_SR, dur=0.25):
    return whoosh(sr, dur=dur, low=800, high=6000, direction="down")


@sfx("alarm", "Alternating two-tone alarm / siren.", freq=(700, "low: Hz or note name"), freq2=(900, "high: Hz or note name"), rate=(4.0, "Hz alternation"), dur=(1.0, "s"), wave=("square", "square|sine|saw"))
def alarm(sr=DEFAULT_SR, freq=700, freq2=900, rate=4.0, dur=1.0, wave="square"):
    n = samples(dur, sr)
    gate = (lfo(dur, rate, sr, "square")[:n] > 0)
    f = np.where(gate, to_hz(freq), to_hz(freq2))
    x = O.osc(wave, f, n, sr)
    x = F.lowpass(x, 5000, sr)
    return x * adsr(dur - 0.02, 0.005, 0.0, 1.0, 0.02, sr)[:n] * 0.5


@sfx("siren", "Smooth rising/falling siren.", low=(500, "Hz"), high=(1000, "Hz"), rate=(0.7, "Hz"), dur=(2.0, "s"))
def siren(sr=DEFAULT_SR, low=500, high=1000, rate=0.7, dur=2.0):
    n = samples(dur, sr)
    f = low + (high - low) * (0.5 + 0.5 * lfo(dur, rate, sr, "triangle")[:n])
    x = F.lowpass(O.saw(f, n, sr), 4000, sr)
    return x * adsr(dur - 0.05, 0.02, 0.0, 1.0, 0.05, sr)[:n] * 0.5


@sfx("error", "Harsh error buzz (two low tones).", freq=(180, "Hz"), dur=(0.3, "s"))
def error(sr=DEFAULT_SR, freq=180, dur=0.3):
    n = samples(dur, sr)
    x = O.square(freq, n, sr) * 0.5 + O.square(freq * 1.06, n, sr) * 0.5
    x = F.lowpass(x, 2500, sr)
    gate = (lfo(dur, 2.0 / dur, sr, "square")[:n] > 0).astype(float)
    return x * adsr(dur - 0.02, 0.003, 0.0, 1.0, 0.02, sr)[:n] * (0.4 + 0.6 * gate) * 0.5


@sfx("success", "Bright rising two-note confirm.", freq=("E5", "first note or Hz"), up=(7, "semitones"), wave=("sine", "sine|triangle|square"))
def success(sr=DEFAULT_SR, freq="E5", up=7, wave="sine"):
    f1 = to_hz(freq)
    f2 = f1 * 2 ** (up / 12)
    d1, d2 = 0.1, 0.35
    a = O.osc(wave, f1, samples(d1 + 0.02, sr), sr) * adsr(d1, 0.005, 0.0, 1.0, 0.02, sr)
    b = O.osc(wave, f2, samples(d2 + 0.1, sr), sr) * adsr(d2, 0.005, 0.15, 0.6, 0.1, sr)
    return mix([(a, 0), (b, d1)], sr) * 0.7


@sfx("proximity", "Repeating proximity beep (faster = closer).", freq=(1000, "Hz"), rate=(4.0, "beeps per second"), dur=(1.0, "total s"), width=(0.4, "beep length as fraction of period"))
def proximity(sr=DEFAULT_SR, freq=1000, rate=4.0, dur=1.0, width=0.4):
    period = 1.0 / rate
    parts = []
    t = 0.0
    while t < dur - 1e-6:
        parts.append((beep(sr, freq=freq, dur=period * width), t))
        t += period
    return mix(parts, sr)


@sfx("radar", "Radar ping with echo tail.", freq=(1200, "Hz or note name (110, '110hz' or 'A2')"))
def radar(sr=DEFAULT_SR, freq=1200):
    n = samples(0.6, sr)
    f = to_hz(freq) * (1 + 0.3 * _dec(n, 0.05, sr))
    x = O.sine(f, n, sr) * _dec(n, 0.12, sr)
    return x * perc(0.6, 0.002, sr, curve=1.0) * 0.8


@sfx("riser", "Tension riser (noise + pitch climbing).", dur=(2.0, "s"), start=(100, "Hz"), end=(2000, "Hz"))
def riser(sr=DEFAULT_SR, dur=2.0, start=100, end=2000):
    n = samples(dur, sr)
    f = O.sweep(start, end, dur, sr)
    tone = O.saw(f, n, sr) * 0.4
    nz = F.biquad(O.white(n, seed=28), "bandpass", f * 4, sr, q=0.8)
    env = np.linspace(0, 1, n) ** 2
    y = (tone + nz) * env
    return F.highpass(y, 80, sr) * 0.8


@sfx("sweep_up", "Pure tone sweep upward.", start=(200, "Hz"), end=(2000, "Hz"), dur=(0.4, "s"), wave=("sine", "sine|saw|square"))
def sweep_up(sr=DEFAULT_SR, start=200, end=2000, dur=0.4, wave="sine"):
    f = O.sweep(start, end, dur, sr)
    n = f.shape[0]
    return O.osc(wave, f, n, sr) * adsr(dur - 0.05, 0.01, 0.0, 1.0, 0.05, sr)[:n] * 0.6


@sfx("sweep_down", "Pure tone sweep downward.", start=(2000, "Hz"), end=(200, "Hz"), dur=(0.4, "s"), wave=("sine", "sine|saw|square"))
def sweep_down(sr=DEFAULT_SR, start=2000, end=200, dur=0.4, wave="sine"):
    return sweep_up(sr, start, end, dur, wave)


@sfx("bubble", "Watery bubble/drop.", freq=(400, "Hz"))
def bubble(sr=DEFAULT_SR, freq=400):
    n = samples(0.15, sr)
    f = freq * (1 + 1.5 * np.linspace(0, 1, n) ** 2)
    return O.sine(f, n, sr) * _dec(n, 0.05, sr) * perc(0.15, 0.002, sr, curve=1.0) * 0.8


@sfx("glitch", "Digital glitch burst.", dur=(0.2, "s"))
def glitch(sr=DEFAULT_SR, dur=0.2):
    n = samples(dur, sr)
    rng = np.random.default_rng(29)
    y = np.zeros(n)
    seg = samples(0.012, sr)
    for s in range(0, n, seg):
        f = rng.choice([220, 440, 880, 1760, 3520]) * rng.uniform(0.9, 1.1)
        e = min(n, s + seg)
        y[s:e] = O.square(f, e - s, sr) * rng.uniform(0.2, 1.0)
    y = np.round(y * 6) / 6
    return y * perc(dur, 0.001, sr, curve=0.8) * 0.5


@sfx("static", "Radio static / white noise burst.", dur=(0.5, "s"), color=("white", "white|pink|brown"))
def static(sr=DEFAULT_SR, dur=0.5, color="white"):
    n = samples(dur, sr)
    return O.noise(n, color, seed=30, sr=sr) * adsr(dur - 0.02, 0.005, 0.0, 1.0, 0.02, sr)[:n] * 0.5


@sfx("wind", "Wind gust.", dur=(3.0, "s"))
def wind(sr=DEFAULT_SR, dur=3.0):
    n = samples(dur, sr)
    fc = 300 + 700 * (0.5 + 0.5 * lfo(dur, 0.25, sr)[:n]) + 200 * lfo(dur, 1.3, sr, "random")[:n]
    y = F.biquad(O.pink(n, seed=31), "bandpass", fc, sr, q=0.7)
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 0.7
    return y * env * 1.2


@sfx("thunder", "Distant thunder rumble.", dur=(2.5, "s"))
def thunder(sr=DEFAULT_SR, dur=2.5):
    n = samples(dur, sr)
    y = F.lowpass(O.brown(n, seed=32), 200, sr, order=2)
    env = _dec(n, dur / 3, sr) * (0.6 + 0.4 * (0.5 + 0.5 * lfo(dur, 3.0, sr, "random")[:n]))
    return np.tanh(y * 3 * env) * perc(dur, 0.05, sr, curve=1.0)


@sfx("footstep", "Footstep on hard floor.", tone=(120, "Hz thump"))
def footstep(sr=DEFAULT_SR, tone=120):
    n = samples(0.15, sr)
    thump = O.sine(tone * (1 + _dec(n, 0.01, sr)), n, sr) * _dec(n, 0.03, sr)
    scuff = F.bandpass(O.white(n, seed=33), 1500, sr, 0.6) * _dec(n, 0.02, sr) * 0.5
    return np.tanh((thump + scuff) * 1.5) * perc(0.15, 0.002, sr, curve=1.0) * 0.8


@sfx("door", "Door thud/close.")
def door(sr=DEFAULT_SR):
    n = samples(0.35, sr)
    thud = O.sine(70 * (1 + 2 * _dec(n, 0.02, sr)), n, sr) * _dec(n, 0.08, sr)
    latch = F.bandpass(O.white(n, seed=34), 2500, sr, 1.0) * _dec(n, 0.01, sr) * 0.6
    latch = np.concatenate([np.zeros(samples(0.04, sr)), latch])[:n]
    return np.tanh((thud + latch) * 2) * perc(0.35, 0.002, sr, curve=1.0) * 0.9


@sfx("engine", "Engine hum loop-able.", rpm=(60, "Hz base"), dur=(2.0, "s"))
def engine(sr=DEFAULT_SR, rpm=60, dur=2.0):
    n = samples(dur, sr)
    f = rpm * (1 + 0.02 * lfo(dur, 7.0, sr, "random")[:n])
    y = O.saw(f, n, sr) * 0.5 + O.pulse(f * 0.5, n, sr, width=0.3) * 0.5
    y = F.lowpass(y, 800, sr, 1.5)
    y += F.lowpass(O.brown(n, seed=35), 300, sr) * 0.3
    return np.tanh(y * 1.5) * adsr(dur - 0.05, 0.05, 0.0, 1.0, 0.05, sr)[:n] * 0.6


@sfx("magic", "Sparkly magic shimmer (random high bell notes).", dur=(0.8, "s"), density=(12, "notes"), freq=("C6", "base note or Hz"))
def magic(sr=DEFAULT_SR, dur=0.8, density=12, freq="C6"):
    from .instruments import render_note
    rng = np.random.default_rng(36)
    base = to_hz(freq)
    parts = []
    for i in range(int(density)):
        semi = rng.choice([0, 2, 4, 7, 9, 12, 14, 16])
        t = (i / density) * dur * 0.8 * rng.uniform(0.9, 1.1)
        parts.append((render_note("glass", base * 2 ** (semi / 12), 0.1, sr, vel=rng.uniform(0.4, 1.0)) * 0.5, t))
    return mix(parts, sr)


@sfx("heartbeat", "Heartbeat lub-dub.", rate=(1.0, "beats per second"), dur=(2.0, "s"))
def heartbeat(sr=DEFAULT_SR, rate=1.0, dur=2.0):
    parts = []
    t = 0.0
    while t < dur:
        n = samples(0.15, sr)
        lub = O.sine(55 * (1 + _dec(n, 0.03, sr)), n, sr) * _dec(n, 0.05, sr)
        parts.append((np.tanh(lub * 2), t))
        parts.append((np.tanh(lub * 1.5), t + 0.18))
        t += 1.0 / rate
    return F.lowpass(mix(parts, sr), 200, sr)


@sfx("tone", "Plain sustained tone with chosen wave.", freq=(440, "Hz or note name (110, '110hz' or 'A2')"), dur=(1.0, "s"), wave=("sine", "any osc wave"))
def tone(sr=DEFAULT_SR, freq=440, dur=1.0, wave="sine"):
    n = samples(dur, sr)
    x = O.osc(wave, to_hz(freq), n, sr)
    return x * adsr(dur - 0.02, 0.01, 0.0, 1.0, 0.02, sr)[:n] * 0.6


@sfx("noise", "Noise burst with envelope.", dur=(0.3, "s"), color=("white", "white|pink|brown"), attack=(0.005, "s"))
def noise(sr=DEFAULT_SR, dur=0.3, color="white", attack=0.005):
    n = samples(dur, sr)
    return O.noise(n, color, seed=37, sr=sr) * perc(dur, attack, sr) * 0.6


@sfx("typewriter", "Key press clack.")
def typewriter(sr=DEFAULT_SR):
    n = samples(0.06, sr)
    y = F.bandpass(O.white(n, seed=38), 2200, sr, 0.8) * _dec(n, 0.006, sr)
    y += O.sine(900, n, sr) * _dec(n, 0.004, sr) * 0.6
    return np.tanh(y * 3) * 0.8


@sfx("countdown", "Countdown tick: short low tone.", freq=(660, "Hz"))
def countdown(sr=DEFAULT_SR, freq=660):
    return beep(sr, freq=freq, dur=0.08, wave="square") * 0.8


def render_sfx(name: str, sr: int = DEFAULT_SR, **params) -> np.ndarray:
    if name not in REGISTRY:
        raise ValueError(f"unknown sfx {name!r}; run `genny list sfx`")
    entry = REGISTRY[name]
    unknown = [k for k in params if k not in entry["params"]]
    if unknown:
        raise ValueError(f"sfx {name!r} does not accept params {unknown}; allowed: {list(entry['params'])}")
    return entry["fn"](sr, **params)


# Registers car_engine into REGISTRY (kept in its own module).
from . import vehicle  # noqa: E402,F401
# Pinball foley (solenoid, knocker, steel_ball, ...).
from . import pinball  # noqa: E402,F401

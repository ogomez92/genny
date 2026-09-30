"""Synthesized instruments. Each takes (freq_hz, dur_seconds, sr, vel, **params) and returns a mono buffer.

The returned buffer may be longer than `dur` because the release tail is appended.
"""
from __future__ import annotations

import numpy as np

from . import filters as F
from . import osc as O
from .core import DEFAULT_SR, samples
from .env import adsr, apply, decay, lfo, perc

REGISTRY: dict[str, dict] = {}


def instrument(name: str, desc: str, **params):
    def deco(fn):
        REGISTRY[name] = {"fn": fn, "desc": desc, "params": params}
        return fn
    return deco


def _n(dur, sr, extra=0.0):
    return samples(dur + extra, sr)


@instrument("piano", "Acoustic-ish piano: inharmonic partials, hammer noise, velocity-sensitive brightness.",
            decay=(2.5, "seconds of ring"), bright=(1.0, "0.5..2"))
def piano(freq, dur, sr=DEFAULT_SR, vel=1.0, decay=2.5, bright=1.0):
    ring = min(decay, dur + 1.5)
    n = _n(ring, sr)
    partials = []
    for h in range(1, 14):
        amp = (1.0 / h ** (1.3 / bright)) * (1.0 if h % 2 else 0.85)
        dec = ring / (1 + 0.35 * (h - 1))
        partials.append((h, amp, dec))
    x = O.additive(freq, n, sr, partials, inharmonic=0.0004)
    hammer = O.white(n, seed=3) * decay_env(n, 0.006, sr) * 0.15 * vel
    hammer = F.bandpass(hammer, min(freq * 6, 8000), sr, 0.6)
    env = np.ones(n)
    a = samples(0.003, sr)
    env[:a] = np.linspace(0, 1, a)
    # note-off: shorten after dur
    off = samples(dur, sr)
    if off < n:
        rel = samples(0.25, sr)
        e2 = np.exp(-np.arange(n - off) / max(rel / 4, 1))
        env[off:] *= e2
    y = (x + hammer) * env
    y = F.lowpass(y, 1200 + 8000 * vel * bright, sr, 0.6)
    return y * (0.35 + 0.65 * vel)


def decay_env(n, tau, sr):
    return np.exp(-np.arange(n) / (tau * sr))


@instrument("epiano", "Electric piano (FM tine).", tremolo=(0.2, "0..1 wobble"), decay=(1.8, "seconds"))
def epiano(freq, dur, sr=DEFAULT_SR, vel=1.0, tremolo=0.2, decay=1.8):
    ring = min(decay, dur + 1.0)
    n = _n(ring, sr)
    idx = 2.5 * vel * decay_env(n, 0.35, sr) + 0.15
    tine = O.fm(freq, n, sr, ratio=1.0, index=idx)
    bell = O.fm(freq, n, sr, ratio=14.0, index=0.3 * vel * decay_env(n, 0.05, sr)) * 0.2
    env = decay_env(n, ring / 3, sr)
    off = samples(dur, sr)
    if off < n:
        env[off:] *= np.exp(-np.arange(n - off) / (0.08 * sr))
    y = (tine + bell) * env
    if tremolo > 0:
        y *= 1 - tremolo * 0.5 * (1 + lfo(n / sr, 5.5, sr)[:n])
    return y * (0.4 + 0.6 * vel)


@instrument("pluck", "Karplus-Strong plucked string (guitar/harp-like).", damping=(0.5, "0..1 brightness loss"), decay=(1.5, "seconds"))
def pluck(freq, dur, sr=DEFAULT_SR, vel=1.0, damping=0.5, decay=1.5):
    from scipy.signal import lfilter
    ring = min(decay, dur + 1.0)
    n = _n(ring, sr)
    D = max(2, int(round(sr / freq)))
    burst = np.zeros(n)
    burst[:D] = O.white(D, seed=int(freq) % 997) * vel
    burst[:D] = F.lowpass(burst[:D], 2000 + 8000 * (1 - damping) * vel, sr)
    g = 0.5 * (0.995 + 0.004 * (1 - damping))
    a = np.zeros(D + 2)
    a[0] = 1
    a[D] = -g
    a[D + 1] = -g
    y = lfilter([1.0], a, burst)
    env = np.ones(n)
    off = samples(dur, sr)
    if off < n:
        env[off:] = np.exp(-np.arange(n - off) / (0.12 * sr))
    y = y * env * np.exp(-np.arange(n) / (ring * sr))
    y = F.dc_block(y, sr)
    return y / (np.max(np.abs(y)) + 1e-9) * (0.5 + 0.5 * vel)


@instrument("harp", "Soft bright pluck with long ring.")
def harp(freq, dur, sr=DEFAULT_SR, vel=1.0):
    return pluck(freq, dur, sr, vel, damping=0.25, decay=2.5) * 0.9


@instrument("guitar", "Plucked nylon guitar (darker pluck).")
def guitar(freq, dur, sr=DEFAULT_SR, vel=1.0):
    y = pluck(freq, dur, sr, vel, damping=0.65, decay=1.8)
    return F.lowpass(y, 3500, sr, 0.8)


@instrument("bass", "Fat analog synth bass with filter envelope.", cutoff=(1200, "Hz peak"), res=(1.5, "resonance"), sub=(0.5, "sine sub-oscillator 0..1"))
def bass(freq, dur, sr=DEFAULT_SR, vel=1.0, cutoff=1200, res=1.5, sub=0.5):
    rel = 0.15
    n = _n(dur, sr, rel)
    x = O.saw(freq, n, sr) * 0.6 + O.square(freq * 0.5, n, sr) * 0.3 + sub * O.sine(freq * 0.5, n, sr)
    fenv = 120 + cutoff * vel * decay_env(n, 0.25, sr)
    x = F.biquad(x, "lowpass", fenv, sr, q=res)
    env = adsr(dur, 0.005, 0.15, 0.7, rel, sr)
    return apply(x, env) * 0.6 * (0.5 + 0.5 * vel)


@instrument("sub", "Pure sine sub bass with soft click.")
def sub(freq, dur, sr=DEFAULT_SR, vel=1.0):
    n = _n(dur, sr, 0.1)
    x = O.sine(freq, n, sr) + 0.15 * O.sine(freq * 2, n, sr)
    return apply(x, adsr(dur, 0.01, 0.05, 0.9, 0.1, sr)) * 0.8


@instrument("lead", "Bright supersaw lead.", detune=(0.3, "semitones spread"), cutoff=(6000, "Hz"))
def lead(freq, dur, sr=DEFAULT_SR, vel=1.0, detune=0.3, cutoff=6000):
    rel = 0.2
    n = _n(dur, sr, rel)
    x = O.supersaw(freq, n, sr, voices=5, detune=detune)
    fenv = cutoff * (0.3 + 0.7 * decay_env(n, 0.4, sr))
    x = F.biquad(x, "lowpass", fenv, sr, q=1.0)
    return apply(x, adsr(dur, 0.01, 0.2, 0.75, rel, sr)) * 0.5 * (0.5 + 0.5 * vel)


@instrument("pad", "Warm slow-attack synth pad (stereo when chorused).", attack=(0.4, "s"), release=(0.8, "s"), cutoff=(2500, "Hz"))
def pad(freq, dur, sr=DEFAULT_SR, vel=1.0, attack=0.4, release=0.8, cutoff=2500):
    n = _n(dur, sr, release)
    x = O.supersaw(freq, n, sr, voices=7, detune=0.35) * 0.7 + O.sine(freq * 0.5, n, sr) * 0.3
    x = F.lowpass(x, cutoff, sr, 0.8)
    return apply(x, adsr(dur, attack, 0.3, 0.8, release, sr)) * 0.45 * (0.6 + 0.4 * vel)


@instrument("strings", "String ensemble: detuned saws, slow attack, vibrato.", attack=(0.25, "s"), release=(0.5, "s"))
def strings(freq, dur, sr=DEFAULT_SR, vel=1.0, attack=0.25, release=0.5):
    n = _n(dur, sr, release)
    vib = freq * (1 + 0.004 * lfo(n / sr, 5.0, sr)[:n] * np.minimum(np.arange(n) / (0.4 * sr), 1))
    x = O.supersaw(vib, n, sr, voices=6, detune=0.25)
    x = F.lowpass(x, 3500, sr, 0.7)
    x = F.peak(x, 800, sr, 1.2, 3)
    return apply(x, adsr(dur, attack, 0.3, 0.85, release, sr, curve=1.5)) * 0.4 * (0.6 + 0.4 * vel)


@instrument("brass", "Synth brass with opening filter (fanfare).", attack=(0.06, "s"))
def brass(freq, dur, sr=DEFAULT_SR, vel=1.0, attack=0.06):
    rel = 0.25
    n = _n(dur, sr, rel)
    x = O.saw(freq, n, sr) * 0.7 + O.saw(freq * 1.005, n, sr) * 0.3
    t = np.arange(n) / sr
    fenv = 400 + 4500 * vel * (1 - np.exp(-t / 0.08)) * (0.6 + 0.4 * np.exp(-t / 0.5))
    x = F.biquad(x, "lowpass", fenv, sr, q=1.4)
    return apply(x, adsr(dur, attack, 0.1, 0.85, rel, sr)) * 0.55 * (0.5 + 0.5 * vel)


@instrument("organ", "Drawbar organ with rotary wobble.", rotary=(0.3, "0..1"))
def organ(freq, dur, sr=DEFAULT_SR, vel=1.0, rotary=0.3):
    rel = 0.05
    n = _n(dur, sr, rel)
    x = O.organ(freq, n, sr)
    if rotary > 0:
        x *= 1 - rotary * 0.3 * (1 + lfo(n / sr, 6.0, sr)[:n]) / 2
    return apply(x, adsr(dur, 0.01, 0.0, 1.0, rel, sr)) * 0.7


@instrument("bell", "FM bell / chime (notifications, magic).", decay=(2.0, "seconds"), ratio=(3.5, "modulator ratio; 2=softer, 5.04=glassy"))
def bell(freq, dur, sr=DEFAULT_SR, vel=1.0, decay=2.0, ratio=3.5):
    ring = max(dur, decay)
    n = _n(ring, sr)
    idx = (1.5 + 2.0 * vel) * decay_env(n, ring / 4, sr)
    x = O.fm(freq, n, sr, ratio=ratio, index=idx)
    x += 0.3 * O.sine(freq * 2.01, n, sr) * decay_env(n, ring / 6, sr)
    return x * decay_env(n, ring / 3, sr) * perc(ring, 0.002, sr, curve=1.2) * 0.7


@instrument("glass", "Glassy high FM tone (UI, crystal).")
def glass(freq, dur, sr=DEFAULT_SR, vel=1.0):
    return bell(freq, dur, sr, vel, decay=max(dur, 0.8), ratio=5.04) * 0.9


@instrument("marimba", "Wooden mallet (marimba/xylophone).", decay=(0.6, "seconds"))
def marimba(freq, dur, sr=DEFAULT_SR, vel=1.0, decay=0.6):
    n = _n(max(dur, decay), sr)
    x = O.sine(freq, n, sr) * decay_env(n, decay / 2, sr)
    x += 0.35 * O.sine(freq * 4.0, n, sr) * decay_env(n, decay / 8, sr)
    x += 0.15 * O.sine(freq * 10.0, n, sr) * decay_env(n, decay / 20, sr)
    click = O.white(n, seed=11) * decay_env(n, 0.003, sr) * 0.2
    return (x + click) * perc(max(dur, decay), 0.001, sr, curve=1.0) * (0.6 + 0.4 * vel)


@instrument("kalimba", "Thumb piano: metallic soft pluck.")
def kalimba(freq, dur, sr=DEFAULT_SR, vel=1.0):
    n = _n(max(dur, 1.2), sr)
    x = O.sine(freq, n, sr) * decay_env(n, 0.5, sr)
    x += 0.4 * O.sine(freq * 6.27, n, sr) * decay_env(n, 0.06, sr)
    x += 0.2 * O.sine(freq * 2.0, n, sr) * decay_env(n, 0.3, sr)
    return x * perc(max(dur, 1.2), 0.001, sr, curve=1.0) * 0.8 * (0.6 + 0.4 * vel)


@instrument("vibraphone", "Vibraphone with tremolo shimmer.")
def vibraphone(freq, dur, sr=DEFAULT_SR, vel=1.0):
    n = _n(max(dur, 1.8), sr)
    x = O.sine(freq, n, sr) * decay_env(n, 0.9, sr) + 0.3 * O.sine(freq * 4, n, sr) * decay_env(n, 0.3, sr)
    x *= 1 - 0.3 * (1 + lfo(n / sr, 4.5, sr)[:n]) / 2
    return x * perc(max(dur, 1.8), 0.002, sr, curve=1.0) * 0.8


@instrument("flute", "Breathy flute (sine + noise + vibrato).", breath=(0.15, "noise amount"))
def flute(freq, dur, sr=DEFAULT_SR, vel=1.0, breath=0.15):
    rel = 0.15
    n = _n(dur, sr, rel)
    vib = freq * (1 + 0.006 * lfo(n / sr, 5.5, sr)[:n] * np.minimum(np.arange(n) / (0.3 * sr), 1))
    x = O.sine(vib, n, sr) + 0.25 * O.sine(vib * 2, n, sr) + 0.08 * O.sine(vib * 3, n, sr)
    nz = F.bandpass(O.white(n, seed=5), freq * 2, sr, 3.0) * breath
    return apply(x + nz, adsr(dur, 0.08, 0.1, 0.85, rel, sr)) * 0.6


@instrument("choir", "Vowel-formant synth choir (\"aah\").", vowel=("a", "a|e|i|o|u"))
def choir(freq, dur, sr=DEFAULT_SR, vel=1.0, vowel="a"):
    formants = {"a": (800, 1150, 2900), "e": (400, 1600, 2700), "i": (350, 1700, 2700), "o": (450, 800, 2830), "u": (325, 700, 2530)}
    rel = 0.6
    n = _n(dur, sr, rel)
    src = O.supersaw(freq, n, sr, voices=5, detune=0.2)
    y = np.zeros(n)
    for f, g in zip(formants.get(vowel, formants["a"]), (1.0, 0.6, 0.25)):
        y += g * F.bandpass(src, f, sr, 6.0)
    y = y / (np.max(np.abs(y)) + 1e-9)
    return apply(y, adsr(dur, 0.35, 0.3, 0.85, rel, sr)) * 0.5


@instrument("chip", "Chiptune pulse wave (NES/GameBoy).", width=(0.25, "pulse width 0.125|0.25|0.5"), vibrato=(0.0, "0..1"))
def chip(freq, dur, sr=DEFAULT_SR, vel=1.0, width=0.25, vibrato=0.0):
    rel = 0.02
    n = _n(dur, sr, rel)
    f = freq * (1 + 0.01 * vibrato * lfo(n / sr, 6.0, sr)[:n]) if vibrato else freq
    x = O.pulse(f, n, sr, width=width)
    return apply(x, adsr(dur, 0.002, 0.0, 1.0, rel, sr)) * 0.4 * (0.5 + 0.5 * vel)


@instrument("chiptri", "Chiptune triangle (NES bass/lead).")
def chiptri(freq, dur, sr=DEFAULT_SR, vel=1.0):
    n = _n(dur, sr, 0.02)
    x = O.triangle(freq, n, sr)
    x = np.round(x * 8) / 8  # 4-bit steps like the 2A03
    return apply(x, adsr(dur, 0.002, 0.0, 1.0, 0.02, sr)) * 0.5


@instrument("board", "80s pinball/arcade sound-board voice: DAC-gritty pulse with a pitch blip at each onset (bwip).",
            width=(0.35, "pulse width 0.1..0.5"), blip=(7.0, "semitones the onset drops from"), bits=(5, "DAC bit depth (0 = clean)"),
            vibrato=(0.0, "semitones of 9 Hz warble"))
def board(freq, dur, sr=DEFAULT_SR, vel=1.0, width=0.35, blip=7.0, bits=5, vibrato=0.0):
    rel = 0.03
    n = _n(dur, sr, rel)
    semis = blip * decay_env(n, 0.012, sr)
    if vibrato:
        semis = semis + vibrato * lfo(n / sr, 9.0, sr)[:n]
    x = O.pulse(freq * 2 ** (semis / 12), n, sr, width=width)
    if bits:
        q = 2 ** (int(bits) - 1)
        x = np.round(x * q) / q
    x = F.lowpass(x, min(freq * 6, 6000), sr)
    return apply(x, adsr(dur, 0.002, 0.08, 0.6, rel, sr)) * 0.45 * (0.5 + 0.5 * vel)


@instrument("sine", "Pure sine tone with soft envelope.")
def sine(freq, dur, sr=DEFAULT_SR, vel=1.0):
    n = _n(dur, sr, 0.05)
    return apply(O.sine(freq, n, sr), adsr(dur, 0.005, 0.0, 1.0, 0.05, sr)) * 0.7


@instrument("square", "Raw square wave with envelope.")
def square(freq, dur, sr=DEFAULT_SR, vel=1.0):
    n = _n(dur, sr, 0.05)
    return apply(O.square(freq, n, sr), adsr(dur, 0.005, 0.0, 1.0, 0.05, sr)) * 0.4


@instrument("saw", "Raw saw wave with envelope and gentle lowpass.")
def saw(freq, dur, sr=DEFAULT_SR, vel=1.0):
    n = _n(dur, sr, 0.05)
    x = F.lowpass(O.saw(freq, n, sr), 6000, sr)
    return apply(x, adsr(dur, 0.005, 0.0, 1.0, 0.05, sr)) * 0.45


@instrument("synth", "Generic subtractive synth: pick wave, ADSR and filter.",
            wave=("saw", "sine|saw|square|pulse|triangle|supersaw|fm|organ"), attack=(0.01, "s"), decay=(0.1, "s"),
            sustain=(0.7, "0..1"), release=(0.2, "s"), cutoff=(4000, "Hz"), res=(0.8, "resonance"),
            fenv=(0.0, "filter envelope amount Hz added at note start"), detune=(0.3, "supersaw spread"), width=(0.5, "pulse width"),
            ratio=(2.0, "fm ratio"), index=(1.0, "fm index"))
def synth(freq, dur, sr=DEFAULT_SR, vel=1.0, wave="saw", attack=0.01, decay=0.1, sustain=0.7, release=0.2,
          cutoff=4000, res=0.8, fenv=0.0, detune=0.3, width=0.5, ratio=2.0, index=1.0):
    n = _n(dur, sr, release)
    x = O.osc(wave, freq, n, sr, detune=detune, width=width, ratio=ratio, index=index)
    if fenv:
        fc = cutoff + fenv * decay_env(n, max(decay, 0.05), sr)
        x = F.biquad(x, "lowpass", fc, sr, q=res)
    elif cutoff < sr / 2 - 100:
        x = F.lowpass(x, cutoff, sr, res)
    return apply(x, adsr(dur, attack, decay, sustain, release, sr)) * 0.5 * (0.5 + 0.5 * vel)


@instrument("pwm", "Pulse-width-modulated synth (retro/lush).", rate=(0.7, "LFO Hz"))
def pwm(freq, dur, sr=DEFAULT_SR, vel=1.0, rate=0.7):
    rel = 0.25
    n = _n(dur, sr, rel)
    # emulate PWM by mixing two saws with modulated phase offset
    ph = 0.5 + 0.4 * lfo(n / sr, rate, sr)[:n]
    a = O.saw(freq, n, sr)
    t = O.phase(freq, n, sr) % 1.0
    b = 2.0 * ((t + ph) % 1.0) - 1.0
    x = F.lowpass(a - b, 5000, sr)
    return apply(x, adsr(dur, 0.02, 0.2, 0.8, rel, sr)) * 0.45


@instrument("wobble", "Dubstep-style LFO filtered bass.", rate=(4.0, "wobble Hz"))
def wobble(freq, dur, sr=DEFAULT_SR, vel=1.0, rate=4.0):
    n = _n(dur, sr, 0.1)
    x = O.saw(freq, n, sr) + O.square(freq * 0.5, n, sr) * 0.5
    fc = 200 + 2500 * (0.5 + 0.5 * lfo(n / sr, rate, sr)[:n])
    x = F.biquad(x, "lowpass", fc, sr, q=4.0)
    return apply(x, adsr(dur, 0.01, 0.0, 1.0, 0.1, sr)) * 0.4


@instrument("music_box", "Tiny music box tine.")
def music_box(freq, dur, sr=DEFAULT_SR, vel=1.0):
    n = _n(max(dur, 1.0), sr)
    x = O.sine(freq, n, sr) * decay_env(n, 0.35, sr)
    x += 0.5 * O.sine(freq * 3.0, n, sr) * decay_env(n, 0.15, sr)
    x += 0.25 * O.sine(freq * 5.4, n, sr) * decay_env(n, 0.05, sr)
    return x * perc(max(dur, 1.0), 0.0005, sr, curve=1.0) * 0.7


@instrument("steel_drum", "Caribbean steel pan.")
def steel_drum(freq, dur, sr=DEFAULT_SR, vel=1.0):
    n = _n(max(dur, 1.2), sr)
    x = O.fm(freq, n, sr, ratio=2.0, index=1.2 * decay_env(n, 0.15, sr))
    x += 0.4 * O.fm(freq * 2.0, n, sr, ratio=3.0, index=0.5 * decay_env(n, 0.1, sr))
    return x * decay_env(n, 0.45, sr) * perc(max(dur, 1.2), 0.002, sr, curve=1.0) * 0.7


def render_note(name: str, freq: float, dur: float, sr: int = DEFAULT_SR, vel: float = 1.0, **params) -> np.ndarray:
    if name not in REGISTRY:
        raise ValueError(f"unknown instrument {name!r}; run `genny list instruments`")
    entry = REGISTRY[name]
    allowed = entry["params"]
    unknown = [k for k in params if k not in allowed]
    if unknown:
        raise ValueError(f"instrument {name!r} does not accept params {unknown}; allowed: {list(allowed)}")
    return entry["fn"](freq, dur, sr, vel, **params)


def render_chord(name: str, freqs: list[float], dur: float, sr: int = DEFAULT_SR, vel: float = 1.0, strum: float = 0.0, **params) -> np.ndarray:
    """Sum several notes; `strum` delays each successive note by that many seconds."""
    from .core import mix
    parts = [(render_note(name, f, dur, sr, vel, **params), i * strum) for i, f in enumerate(freqs)]
    y = mix(parts, sr)
    return y / np.sqrt(max(1, len(freqs)))

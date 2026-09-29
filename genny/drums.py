"""Drum synthesis. Each takes (sr, vel, **params) and returns a mono buffer."""
from __future__ import annotations

import numpy as np

from . import filters as F
from . import osc as O
from .core import DEFAULT_SR, samples
from .env import perc

REGISTRY: dict[str, dict] = {}


def drum(name: str, desc: str, **params):
    def deco(fn):
        REGISTRY[name] = {"fn": fn, "desc": desc, "params": params}
        return fn
    return deco


def _dec(n, tau, sr):
    return np.exp(-np.arange(n) / (tau * sr))


@drum("kick", "Punchy kick drum.", tune=(55, "Hz body"), decay=(0.4, "s"), punch=(1.0, "click/pitch-drop amount"))
def kick(sr=DEFAULT_SR, vel=1.0, tune=55, decay=0.4, punch=1.0):
    n = samples(decay + 0.1, sr)
    f = tune + tune * 6 * punch * _dec(n, 0.03, sr)
    body = O.sine(f, n, sr) * _dec(n, decay / 3, sr)
    click = F.highpass(O.white(n, seed=1), 2000, sr) * _dec(n, 0.004, sr) * 0.4 * punch
    y = np.tanh((body + click) * 1.8) * perc(decay + 0.1, 0.0005, sr, curve=1.0)
    return y * (0.6 + 0.4 * vel)


@drum("kick808", "Long boomy 808 kick.", tune=(45, "Hz"), decay=(1.2, "s"))
def kick808(sr=DEFAULT_SR, vel=1.0, tune=45, decay=1.2):
    n = samples(decay, sr)
    f = tune + tune * 4 * _dec(n, 0.02, sr)
    y = np.tanh(O.sine(f, n, sr) * 2.5 * _dec(n, decay / 2.5, sr))
    return y * perc(decay, 0.001, sr, curve=1.0) * (0.6 + 0.4 * vel)


@drum("snare", "Snare: tone + noise.", tune=(180, "Hz"), decay=(0.25, "s"), snappy=(0.7, "noise amount"))
def snare(sr=DEFAULT_SR, vel=1.0, tune=180, decay=0.25, snappy=0.7):
    n = samples(decay + 0.05, sr)
    tone = (O.sine(tune + 80 * _dec(n, 0.02, sr), n, sr) + 0.5 * O.sine(tune * 1.6, n, sr)) * _dec(n, decay / 4, sr)
    nz = F.bandpass(O.white(n, seed=2), 3500, sr, 0.5) * _dec(n, decay / 2.2, sr) * snappy * 1.5
    y = np.tanh((tone * 0.8 + nz) * 1.5)
    return y * perc(decay + 0.05, 0.0005, sr, curve=1.0) * (0.5 + 0.5 * vel)


@drum("clap", "Hand clap (multi-burst noise).", decay=(0.3, "s"))
def clap(sr=DEFAULT_SR, vel=1.0, decay=0.3):
    n = samples(decay + 0.05, sr)
    nz = F.bandpass(O.white(n, seed=4), 1500, sr, 0.8)
    env = np.zeros(n)
    for i, t in enumerate((0.0, 0.011, 0.022, 0.033)):
        s = samples(t, sr)
        env[s:] += _dec(n - s, 0.006 if i < 3 else decay / 2.5, sr)
    return np.tanh(nz * env * 2.0) * (0.5 + 0.5 * vel)


@drum("hihat", "Closed hi-hat (metallic noise).", decay=(0.08, "s"), tone=(9000, "Hz brightness"))
def hihat(sr=DEFAULT_SR, vel=1.0, decay=0.08, tone=9000):
    n = samples(decay + 0.02, sr)
    metal = sum(O.square(f, n, sr) for f in (296, 410, 522, 663, 781, 934)) / 6
    y = F.highpass(metal * 0.5 + O.white(n, seed=6) * 0.5, tone * 0.7, sr, order=2)
    y = F.peak(y, tone, sr, 1.5, 4)
    return y * _dec(n, decay / 3, sr) * perc(decay + 0.02, 0.0005, sr, curve=1.0) * 0.8 * (0.5 + 0.5 * vel)


@drum("openhat", "Open hi-hat.", decay=(0.4, "s"))
def openhat(sr=DEFAULT_SR, vel=1.0, decay=0.4):
    return hihat(sr, vel, decay=decay, tone=8000)


@drum("tom", "Tom drum.", tune=(120, "Hz"), decay=(0.35, "s"))
def tom(sr=DEFAULT_SR, vel=1.0, tune=120, decay=0.35):
    n = samples(decay + 0.05, sr)
    f = tune * (1 + 0.8 * _dec(n, 0.04, sr))
    y = O.sine(f, n, sr) * _dec(n, decay / 3, sr) + 0.15 * F.bandpass(O.white(n, seed=8), tune * 4, sr, 1.0) * _dec(n, 0.02, sr)
    return np.tanh(y * 1.5) * perc(decay + 0.05, 0.001, sr, curve=1.0) * (0.6 + 0.4 * vel)


@drum("rim", "Rimshot / side stick.")
def rim(sr=DEFAULT_SR, vel=1.0):
    n = samples(0.08, sr)
    y = O.square(1800, n, sr) * _dec(n, 0.004, sr) + O.sine(450, n, sr) * _dec(n, 0.012, sr) * 0.8
    y += F.highpass(O.white(n, seed=9), 4000, sr) * _dec(n, 0.003, sr) * 0.5
    return np.tanh(y * 1.5) * 0.8 * (0.5 + 0.5 * vel)


@drum("cowbell", "808 cowbell.", decay=(0.3, "s"))
def cowbell(sr=DEFAULT_SR, vel=1.0, decay=0.3):
    n = samples(decay, sr)
    y = (O.square(587, n, sr) + O.square(845, n, sr)) * 0.5
    y = F.bandpass(y, 700, sr, 1.0) * _dec(n, decay / 4, sr)
    return np.tanh(y * 3) * 0.7 * (0.5 + 0.5 * vel)


@drum("crash", "Crash cymbal.", decay=(1.5, "s"))
def crash(sr=DEFAULT_SR, vel=1.0, decay=1.5):
    n = samples(decay, sr)
    metal = sum(O.square(f * 1.7, n, sr) for f in (296, 410, 522, 663, 781, 934)) / 6
    y = F.highpass(metal * 0.4 + O.white(n, seed=10) * 0.6, 4000, sr, order=2)
    y = F.peak(y, 7000, sr, 0.8, 3)
    return y * _dec(n, decay / 3, sr) * perc(decay, 0.001, sr, curve=1.0) * 0.7 * (0.5 + 0.5 * vel)


@drum("ride", "Ride cymbal ping.", decay=(1.0, "s"))
def ride(sr=DEFAULT_SR, vel=1.0, decay=1.0):
    n = samples(decay, sr)
    ping = O.sine(3200, n, sr) * _dec(n, 0.15, sr) * 0.4 + O.fm(1800, n, sr, ratio=1.41, index=3.0) * _dec(n, decay / 3, sr) * 0.3
    wash = F.highpass(O.white(n, seed=12), 6000, sr) * _dec(n, decay / 2.5, sr) * 0.3
    return (ping + wash) * perc(decay, 0.001, sr, curve=1.0) * 0.8 * (0.5 + 0.5 * vel)


@drum("shaker", "Shaker / maraca.", decay=(0.12, "s"))
def shaker(sr=DEFAULT_SR, vel=1.0, decay=0.12):
    n = samples(decay, sr)
    y = F.bandpass(O.white(n, seed=13), 7000, sr, 1.5)
    env = perc(decay, 0.02, sr, curve=2.0)
    return y * env * 0.8 * (0.5 + 0.5 * vel)


@drum("tambourine", "Tambourine jingle.", decay=(0.25, "s"))
def tambourine(sr=DEFAULT_SR, vel=1.0, decay=0.25):
    n = samples(decay, sr)
    y = np.zeros(n)
    for i, f in enumerate((5200, 6100, 7300, 8400)):
        y += O.fm(f, n, sr, ratio=1.3, index=2.0) * _dec(n, decay / (3 + i), sr) * 0.2
    y += F.highpass(O.white(n, seed=14), 5000, sr) * _dec(n, decay / 4, sr) * 0.4
    return y * perc(decay, 0.001, sr, curve=1.0) * 0.8 * (0.5 + 0.5 * vel)


@drum("woodblock", "Wood block / clave.", tune=(1100, "Hz"))
def woodblock(sr=DEFAULT_SR, vel=1.0, tune=1100):
    n = samples(0.12, sr)
    y = O.sine(tune, n, sr) * _dec(n, 0.02, sr) + O.sine(tune * 2.4, n, sr) * _dec(n, 0.01, sr) * 0.4
    return np.tanh(y * 1.5) * perc(0.12, 0.0005, sr, curve=1.0) * 0.8 * (0.5 + 0.5 * vel)


@drum("taiko", "Big deep taiko / cinematic drum.", tune=(60, "Hz"), decay=(0.9, "s"))
def taiko(sr=DEFAULT_SR, vel=1.0, tune=60, decay=0.9):
    n = samples(decay, sr)
    f = tune * (1 + 1.5 * _dec(n, 0.05, sr))
    body = O.sine(f, n, sr) * _dec(n, decay / 3, sr) + 0.3 * O.sine(f * 1.5, n, sr) * _dec(n, decay / 6, sr)
    skin = F.bandpass(O.brown(n, seed=15), 300, sr, 0.8) * _dec(n, 0.08, sr) * 0.8
    return np.tanh((body + skin) * 2.0) * perc(decay, 0.002, sr, curve=1.0) * (0.6 + 0.4 * vel)


@drum("zap_kick", "Electronic laser-kick hybrid.", decay=(0.3, "s"))
def zap_kick(sr=DEFAULT_SR, vel=1.0, decay=0.3):
    n = samples(decay, sr)
    f = 50 + 1500 * _dec(n, 0.03, sr)
    return np.tanh(O.sine(f, n, sr) * 2 * _dec(n, decay / 3, sr)) * perc(decay, 0.0005, sr, curve=1.0) * (0.6 + 0.4 * vel)


def render_drum(name: str, sr: int = DEFAULT_SR, vel: float = 1.0, **params) -> np.ndarray:
    if name not in REGISTRY:
        raise ValueError(f"unknown drum {name!r}; run `genny list drums`")
    entry = REGISTRY[name]
    unknown = [k for k in params if k not in entry["params"]]
    if unknown:
        raise ValueError(f"drum {name!r} does not accept params {unknown}; allowed: {list(entry['params'])}")
    return entry["fn"](sr, vel, **params)

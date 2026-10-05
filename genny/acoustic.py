"""Acoustic instruments: more keys, mallets and bells, plucked and bowed strings, winds and brass.

Registered into the instrument REGISTRY (imported at the bottom of instruments.py). Three engines:
  - `_string` (tuned Karplus-Strong) for everything plucked or struck on a string,
  - `_modes` (rolled-off inharmonic partials) for bars, bells, bowls and drums with a pitch,
  - `_blown` (a band-limited harmonic stack shaped by fixed body formants, whose brightness opens
    with the attack and velocity) for bowed strings, reeds, flutes and brass.
All three follow the voicing rules at the top of instruments.py: brightness is set in Hz, not in
harmonics, so nothing turns piercing as it climbs.
"""
from __future__ import annotations

import numpy as np

from . import filters as F
from . import osc as O
from .core import DEFAULT_SR, mix
from .env import adsr, apply, lfo, perc
from .instruments import (_cut, _harmonics, _ks, _kt, _modes, _n, _off, _roll, _spectrum, _string, _vibrato,
                          decay_env, instrument)


# ---------------------------------------------------------------- keys
@instrument("wurli", "Wurlitzer-style reed electric piano: hollow and a little nasal, growls when hit hard (soul, indie, lo-fi).",
            family="keys", span=("C2", "C6"), tremolo=(0.3, "0..1 wobble"), decay=(1.4, "seconds"))
def wurli(freq, dur, sr=DEFAULT_SR, vel=1.0, tremolo=0.3, decay=1.4):
    ring = min(decay, dur + 0.8)
    n = _n(ring, sr)
    drive = (0.5 + _kt(freq, 2.4, 0.7) * vel) * decay_env(n, 0.22, sr) + 0.5
    # a reed swinging past a pickup is lopsided: even and odd harmonics
    x = np.tanh(drive * (O.sine(freq, n, sr) + 0.25)) - np.tanh(drive * 0.25)
    x = F.lowpass(F.dc_block(x, sr), _cut(freq, 5, 1200, 3000), sr, 0.8, order=2)
    env = decay_env(n, ring / 2.5, sr) * _off(n, dur, sr, 0.06) * perc(ring, 0.002, sr, curve=0.6)
    if tremolo > 0:
        env = env * (1 - tremolo * 0.5 * (1 + lfo(n / sr, 5.8, sr)[:n]))
    return x * env * (0.4 + 0.6 * vel)


@instrument("clav", "Clavinet: short, funky, nasal struck string (funk, disco, reggae skank).",
            family="keys", span=("C2", "C6"), decay=(0.9, "seconds"), bright=(1.0, "0.5 muted .. 1.5 biting"))
def clav(freq, dur, sr=DEFAULT_SR, vel=1.0, decay=0.9, bright=1.0):
    y = _string(freq, dur, sr, vel, t60=decay * 1.5, bright=3400 * bright, damp=0.15, pick=0.1, grit=0.1, release=0.03, tail=0.25)
    y = F.peak(F.highpass(y, max(120.0, freq * 0.6), sr), 1500, sr, 1.0, 5.0)
    return F.lowpass(y, 4200, sr, 0.7) * 0.8


@instrument("harpsichord", "Harpsichord: quill-plucked strings with a 4-foot octave rank; bright but thin, not velocity sensitive.",
            family="keys", span=("C2", "C6"))
def harpsichord(freq, dur, sr=DEFAULT_SR, vel=1.0):
    y = _string(freq, dur, sr, 0.9, t60=2.4, bright=4000, damp=0.12, pick=0.1, grit=0.15, release=0.05, tail=0.5)
    y4 = _string(freq * 2, dur, sr, 0.8, t60=1.6, bright=3600, damp=0.15, pick=0.12, grit=0.15, release=0.05, tail=0.5, seed=5)
    y = mix([(y, 0.0), (y4 * 0.3, 0.0)], sr)
    return F.lowpass(F.highpass(y, 110, sr), 4500, sr, 0.7) * (0.8 + 0.2 * vel)


@instrument("celesta", "Celesta: felt hammers on steel plates over wooden resonators; a soft, round bell (lullabies, fairy music).",
            family="mallet", span=("C4", "C8"))
def celesta(freq, dur, sr=DEFAULT_SR, vel=1.0):
    ring = max(dur, 1.3 * _kt(freq, 1.0, 0.6, f_lo=523.0, f_hi=4186.0))
    n = _n(ring, sr)
    x = _modes(freq, n, sr, [(1.0, 1.0, ring / 2.5), (2.0, 0.2, ring / 5), (5.1, 0.14 * vel, 0.04)], corner=3000.0)
    return x * perc(ring, 0.002, sr, curve=1.0) * 0.75 * (0.6 + 0.4 * vel)


@instrument("toy_piano", "Toy piano: plastic hammers on metal rods; plinky, childlike, a little out of true.",
            family="mallet", span=("C4", "C7"))
def toy_piano(freq, dur, sr=DEFAULT_SR, vel=1.0):
    ring = max(dur, 0.7)
    n = _n(ring, sr)
    x = _modes(freq, n, sr, [(1.0, 1.0, 0.3), (2.93, 0.3, 0.1), (6.27, 0.2 * vel, 0.03)], corner=3000.0)
    click = F.bandpass(O.white(n, seed=21), _cut(freq, 4, 1500, 3000), sr, 3.0) * decay_env(n, 0.004, sr) * 0.25 * vel
    return (x + click) * perc(ring, 0.001, sr, curve=1.0) * 0.75 * (0.6 + 0.4 * vel)


@instrument("church_organ", "Pipe organ: principal ranks at several octaves that speak slowly with a little chiff (add a long reverb).",
            family="keys", span=("C2", "C6"), sub=(0.35, "16-foot sub-octave rank 0..1"), mixture=(0.5, "upper ranks 0..1"))
def church_organ(freq, dur, sr=DEFAULT_SR, vel=1.0, sub=0.35, mixture=0.5):
    rel = 0.2
    n = _n(dur, sr, rel)
    x = np.zeros(n)
    for mult, g, tune in ((0.5, sub, 1.0003), (1, 1.0, 1.0), (2, 0.45, 0.9996), (3, 0.3 * mixture, 1.0004), (4, 0.4 * mixture, 1.0005)):
        f = freq * mult
        if g <= 0 or f > 5000:
            continue
        x += g * _harmonics(f * tune, n, sr, _spectrum(f, sr, tilt=1.7, corner=2400.0, slope=2.5, top=5000.0, maxh=10))
    chiff = F.bandpass(O.white(n, seed=31), _cut(freq, 3, 600, 2400), sr, 2.0) * decay_env(n, 0.03, sr) * 0.12
    return apply(x / 1.6 + chiff, adsr(dur, 0.05, 0.0, 1.0, rel, sr, curve=1.2)) * 0.6


@instrument("accordion", "Accordion: two or three reeds tuned slightly apart (musette shimmer) under bellows pressure (folk, tango, polka, chanson).",
            family="keys", span=("C3", "C6"), musette=(9.0, "cents the reeds are tuned apart (0 = dry single reed)"))
def accordion(freq, dur, sr=DEFAULT_SR, vel=1.0, musette=9.0):
    rel = 0.08
    n = _n(dur, sr, rel)
    amps = _spectrum(freq, sr, tilt=1.0, formants=[(900, 400, 0.8)], corner=2200.0, slope=2.5, top=5500.0, even=0.7)
    reeds = ((0.0, 1.0), (musette, 0.7), (-0.8 * musette, 0.5)) if musette else ((0.0, 1.0),)
    x = sum(g * _harmonics(freq * 2 ** (c / 1200.0), n, sr, amps) for c, g in reeds) / 1.5
    t = np.arange(n) / sr
    x = x * (1 + 0.05 * np.sin(2 * np.pi * 0.9 * t))   # bellows
    return apply(x, adsr(dur, 0.045, 0.1, 0.9, rel, sr, curve=1.3)) * 0.6 * (0.5 + 0.5 * vel)


# ---------------------------------------------------------------- mallets / bells / pitched drums
@instrument("xylophone", "Xylophone: hard mallets on short wooden bars; dry, bright knock (cartoons, puzzles).",
            family="mallet", span=("F4", "C8"))
def xylophone(freq, dur, sr=DEFAULT_SR, vel=1.0):
    ring = max(dur, 0.4 * _kt(freq, 1.2, 0.7, f_lo=350.0, f_hi=4186.0))
    n = _n(ring, sr)
    x = _modes(freq, n, sr, [(1.0, 1.0, ring / 3), (3.0, 0.35 * vel, ring / 8), (6.0, 0.12 * vel, ring / 18)], corner=3000.0)
    click = F.bandpass(O.white(n, seed=22), _cut(freq, 3, 1200, 2600), sr, 1.0) * decay_env(n, 0.003, sr) * 0.18 * vel
    return (x + click) * perc(ring, 0.0008, sr, curve=1.0) * 0.8 * (0.6 + 0.4 * vel)


@instrument("glockenspiel", "Glockenspiel: small steel bars; a clear, sweet ring for high sparkle lines.",
            family="mallet", span=("G5", "C8"))
def glockenspiel(freq, dur, sr=DEFAULT_SR, vel=1.0):
    ring = max(dur, 1.4 * _kt(freq, 1.0, 0.6, f_lo=784.0, f_hi=4186.0))
    n = _n(ring, sr)
    x = _modes(freq, n, sr, [(1.0, 1.0, ring / 2.5), (2.76, 0.28 * vel, ring / 8), (5.4, 0.1 * vel, 0.05)], corner=3400.0, beat=0.8)
    return x * perc(ring, 0.001, sr, curve=1.0) * 0.7 * (0.6 + 0.4 * vel)


@instrument("handpan", "Handpan / hang drum: a hand-struck steel dome ringing its octave and fifth (ambient, meditative, world).",
            family="mallet", span=("C3", "C5"))
def handpan(freq, dur, sr=DEFAULT_SR, vel=1.0):
    ring = max(dur, 1.8)
    n = _n(ring, sr)
    x = _modes(freq, n, sr, [(1.0, 1.0, 1.0), (2.0, 0.5, 0.75), (3.0, 0.3 * vel, 0.5), (4.16, 0.06 * vel, 0.1)], corner=2500.0, beat=0.7)
    thump = F.lowpass(O.white(n, seed=23), 320, sr) * decay_env(n, 0.012, sr) * 0.6 * vel
    return (x + thump) * perc(ring, 0.003, sr, curve=1.0) * 0.75 * (0.6 + 0.4 * vel)


@instrument("tubular_bell", "Tubular bell / orchestral chime: a tall inharmonic clang whose partials imply the note (clock towers, Christmas, drama).",
            family="mallet", span=("C4", "G5"), decay=(3.5, "seconds"))
def tubular_bell(freq, dur, sr=DEFAULT_SR, vel=1.0, decay=3.5):
    ring = max(dur, decay)
    n = _n(ring, sr)
    x = _modes(freq, n, sr, [(0.615, 0.25, ring / 2.5), (1.0, 0.3, ring / 2.5), (1.21, 0.45, ring / 3), (2.0, 1.0, ring / 3.5),
                             (2.99, 0.8 * vel, ring / 5), (4.17, 0.5 * vel, ring / 8), (5.55, 0.25 * vel, ring / 12)],
               corner=3200.0, beat=0.5)
    return x * perc(ring, 0.002, sr, curve=1.2) * 0.5 * (0.6 + 0.4 * vel)


@instrument("gamelan", "Gamelan metallophone (saron/gender): bronze bars tuned in beating pairs, so every note shimmers.",
            family="mallet", span=("C4", "C7"), ombak=(3.0, "beat rate Hz between the paired bars"))
def gamelan(freq, dur, sr=DEFAULT_SR, vel=1.0, ombak=3.0):
    ring = max(dur, 2.0)
    n = _n(ring, sr)
    x = _modes(freq, n, sr, [(1.0, 1.0, 1.3), (2.71, 0.4 * vel, 0.5), (5.15, 0.15 * vel, 0.12)], corner=3000.0, beat=ombak)
    return x * perc(ring, 0.001, sr, curve=1.0) * 0.7 * (0.6 + 0.4 * vel)


@instrument("singing_bowl", "Singing bowl: very long ring with slowly beating partials (meditation, ambient, temple).",
            family="mallet", span=("C3", "C5"), decay=(6.0, "seconds"))
def singing_bowl(freq, dur, sr=DEFAULT_SR, vel=1.0, decay=6.0):
    ring = max(dur, decay)
    n = _n(ring, sr)
    x = _modes(freq, n, sr, [(1.0, 1.0, ring / 2.2), (2.71, 0.45, ring / 3.5), (5.0, 0.2 * vel, ring / 7)], corner=2600.0, beat=0.6)
    return x * perc(ring, 0.015, sr, curve=1.3) * 0.7 * (0.6 + 0.4 * vel)


@instrument("timpani", "Timpani / kettle drum: a pitched orchestral drum, boom and roll (write it low: C2-C4).",
            family="mallet", span=("C2", "C4"), decay=(1.6, "seconds"))
def timpani(freq, dur, sr=DEFAULT_SR, vel=1.0, decay=1.6):
    ring = max(dur, decay)
    n = _n(ring, sr)
    x = _modes(freq, n, sr, [(1.0, 1.0, ring / 2.5), (1.5, 0.5, ring / 3.5), (1.99, 0.35, ring / 5), (2.44, 0.2 * vel, ring / 7),
                             (0.63, 0.5, 0.07)], corner=1500.0)
    thump = F.lowpass(O.white(n, seed=24), 260, sr) * decay_env(n, 0.02, sr) * 0.9 * vel
    return np.tanh((x + thump) * 1.2) * perc(ring, 0.002, sr, curve=1.0) * 0.7 * (0.5 + 0.5 * vel)


# ---------------------------------------------------------------- plucked strings
def _body(y, sr, peaks, lowpass=None):
    for fc, q, db in peaks:
        y = F.peak(y, fc, sr, q, db)
    return F.lowpass(y, lowpass, sr, 0.7) if lowpass else y


@instrument("steel_guitar", "Steel-string acoustic guitar: bright strum and fingerpicking (folk, country, pop).",
            family="plucked", span=("E2", "E5"))
def steel_guitar(freq, dur, sr=DEFAULT_SR, vel=1.0):
    y = _string(freq, dur, sr, vel, t60=4.5, bright=3800, damp=0.2, pick=0.16, grit=0.3, release=0.12, tail=1.6)
    return _body(y, sr, [(100, 1.2, 3.0), (200, 1.5, 2.0)], 5000)


@instrument("electric_guitar", "Clean electric guitar: round single-coil tone with long sustain (add `distortion` or `chorus` on the layer for rock or jangle).",
            family="plucked", span=("E2", "E6"), tone=(2800, "pickup tone Hz"))
def electric_guitar(freq, dur, sr=DEFAULT_SR, vel=1.0, tone=2800):
    y = _string(freq, dur, sr, vel, t60=5.5, bright=3200, damp=0.25, pick=0.2, grit=0.15, release=0.08, tail=1.2)
    return F.lowpass(F.highpass(y, 70, sr), tone, sr, 1.3)


@instrument("muted_guitar", "Palm-muted electric guitar: short woody chug (funk scratch, reggae skank, rock eighths).",
            family="plucked", span=("E2", "E5"))
def muted_guitar(freq, dur, sr=DEFAULT_SR, vel=1.0):
    y = _string(freq, min(dur, 0.12), sr, vel, t60=0.4, bright=1900, damp=0.5, pick=0.2, grit=0.25, release=0.03, tail=0.2)
    return F.lowpass(F.highpass(y, 70, sr), 2200, sr, 1.2)


@instrument("dist_guitar", "Overdriven electric guitar for riffs and leads; sustains while held (for crunchy chords play `electric_guitar` and put `distortion` on the layer).",
            family="plucked", span=("E2", "E6"), drive=(6.0, "1 = edge of breakup .. 15 = fuzz"), tone=(3000, "cabinet tone Hz"))
def dist_guitar(freq, dur, sr=DEFAULT_SR, vel=1.0, drive=6.0, tone=3000):
    rel = 0.12
    n = _n(dur, sr, rel)
    s = _ks(freq, n, sr, t60=7.0, bright=2600, damp=0.3, pick=0.18, grit=0.15)
    s = F.highpass(s / (np.max(np.abs(s)) + 1e-9), 120, sr)
    y = np.tanh(drive * (0.5 + 0.5 * vel) * s)
    y = F.peak(F.lowpass(F.highpass(y, 90, sr), tone, sr, 0.8, order=2), 1400, sr, 1.0, 3.0)
    return apply(y, adsr(dur, 0.003, 0.0, 1.0, rel, sr)) * 0.5 * (0.6 + 0.4 * vel)


@instrument("banjo", "Banjo: twangy string over a drum head, quick decay (bluegrass, country, folk).",
            family="plucked", span=("C3", "C6"))
def banjo(freq, dur, sr=DEFAULT_SR, vel=1.0):
    y = _string(freq, dur, sr, vel, t60=1.0, bright=4200, damp=0.12, pick=0.08, grit=0.3, release=0.06, tail=0.6)
    y = y + 0.6 * F.bandpass(y, 600, sr, 2.0)
    return F.lowpass(F.highpass(y, 150, sr), 4500, sr, 0.7) * 0.8


@instrument("mandolin", "Mandolin: paired steel strings; set `tremolo` to re-pick held notes (Italian, bluegrass, folk).",
            family="plucked", span=("G3", "E6"), tremolo=(0.0, "picks per second on held notes (12 = classic tremolo, 0 = off)"))
def mandolin(freq, dur, sr=DEFAULT_SR, vel=1.0, tremolo=0.0):
    def one(d, v):
        a = _string(freq, d, sr, v, t60=1.4, bright=4000, damp=0.15, pick=0.12, grit=0.25, release=0.05, tail=0.7)
        b = _string(freq * 1.003, d, sr, v, t60=1.4, bright=4000, damp=0.15, pick=0.12, grit=0.25, release=0.05, tail=0.7, seed=7)
        return mix([(a, 0.0), (b, 0.004)], sr) * 0.6
    if tremolo > 0 and dur * tremolo >= 1.5:
        step = 1.0 / tremolo
        y = mix([(one(step, vel * (1.0 if i % 2 == 0 else 0.82)), i * step) for i in range(int(dur * tremolo))], sr)
    else:
        y = one(dur, vel)
    return F.lowpass(F.highpass(y, 150, sr), 4500, sr, 0.7)


@instrument("koto", "Koto: silk string plucked hard near the bridge with ivory picks (Japanese, East Asian).",
            family="plucked", span=("C3", "C6"))
def koto(freq, dur, sr=DEFAULT_SR, vel=1.0):
    y = _string(freq, dur, sr, vel, t60=2.6, bright=3600, damp=0.2, pick=0.07, grit=0.25, release=0.15, tail=1.4)
    return _body(y, sr, [(300, 1.5, 3.0)], 4200)


@instrument("sitar", "Sitar: long string over a buzzing bridge, the buzz blooms just after the pluck (Indian classical, psychedelic).",
            family="plucked", span=("C3", "C5"), buzz=(0.45, "0..1 amount of bridge buzz"))
def sitar(freq, dur, sr=DEFAULT_SR, vel=1.0, buzz=0.45):
    y = _string(freq, dur, sr, vel, t60=3.5, bright=3400, damp=0.1, pick=0.06, grit=0.3, release=0.2, tail=1.6)
    n = y.shape[0]
    t = np.arange(n) / sr
    b = F.peak(F.highpass(np.tanh(6.0 * y), 700, sr), 2400, sr, 1.2, 4.0) * (1 - np.exp(-t / 0.05)) * np.exp(-t / 0.9)
    return F.lowpass(y + buzz * b, 4200, sr, 0.7, order=2) * 0.8


@instrument("pizzicato", "Pizzicato strings: short, woody finger-plucked violin/cello notes (playful, sneaky, classical).",
            family="plucked", span=("C2", "C6"))
def pizzicato(freq, dur, sr=DEFAULT_SR, vel=1.0):
    y = _string(freq, min(dur, 0.25), sr, vel, t60=0.55, bright=2400, damp=0.45, pick=0.25, grit=0.15, release=0.08, tail=0.4)
    return _body(y, sr, [(290, 1.5, 3.0), (460, 1.5, 3.0), (1000, 1.0, 2.0)], 3200)


# ---------------------------------------------------------------- basses
@instrument("upright_bass", "Upright (double) bass, plucked: deep woody thump with a short singing tail (jazz walking lines, rockabilly, folk).",
            family="bass", span=("E1", "G3"))
def upright_bass(freq, dur, sr=DEFAULT_SR, vel=1.0):
    y = _string(freq, dur, sr, vel, t60=2.0, bright=850, damp=0.5, pick=0.3, grit=0.1, release=0.1, tail=0.8)
    n = y.shape[0]
    thump = F.lowpass(O.white(n, seed=41), 300, sr) * decay_env(n, 0.012, sr) * 0.5 * vel
    return _body(y + thump, sr, [(100, 1.2, 3.0), (210, 1.5, 2.0)], 1400)


@instrument("finger_bass", "Electric bass guitar, fingerstyle: round, even, sustaining (rock, pop, soul, reggae).",
            family="bass", span=("E1", "G3"), tone=(1700, "pickup tone Hz"))
def finger_bass(freq, dur, sr=DEFAULT_SR, vel=1.0, tone=1700):
    y = _string(freq, dur, sr, vel, t60=4.0, bright=1500, damp=0.4, pick=0.28, grit=0.1, release=0.07, tail=0.6)
    return F.lowpass(np.tanh(1.5 * y) / 0.9, tone, sr, 1.0)


@instrument("slap_bass", "Slapped electric bass: percussive pop on top of a scooped, punchy low end (funk, disco).",
            family="bass", span=("E1", "G3"))
def slap_bass(freq, dur, sr=DEFAULT_SR, vel=1.0):
    y = _string(freq, dur, sr, vel, t60=2.6, bright=4200, damp=0.15, pick=0.1, grit=0.3, release=0.05, tail=0.5)
    n = y.shape[0]
    pop = F.bandpass(O.white(n, seed=42), 2300, sr, 1.5) * decay_env(n, 0.004, sr) * 0.3 * vel
    y = F.peak(y + pop, 500, sr, 1.0, -5.0)
    return F.lowpass(F.highpass(y, 35, sr), 4000, sr, 0.7)


# ---------------------------------------------------------------- bowed / blown
def _blown(freq, dur, sr, vel, soft, hard, attack=0.05, release=0.1, bloom=0.06, vib=(5.5, 0.1, 0.2), scoop=0.0,
           sustain=0.9, top=6500.0):
    """Sustained harmonic voice. `soft` / `hard` are `_spectrum` kwargs for the quiet and the loud
    spectrum; the tone opens from soft towards hard as the note speaks (`bloom` seconds) and with
    velocity, which is what makes bowed strings and brass sound played rather than switched on."""
    n = _n(dur, sr, release)
    f = _vibrato(freq, n, sr, rate=vib[0], depth=vib[1], delay=vib[2], ramp=0.3, scoop=scoop)
    a0 = _spectrum(freq, sr, top=top, **soft)
    a1 = _spectrum(freq, sr, top=top, **hard)
    K = max(len(a0), len(a1))
    a0 = np.pad(a0, (0, K - len(a0)))
    a1 = np.pad(a1, (0, K - len(a1)))
    t = np.arange(n) / sr
    b = (0.25 + 0.75 * vel) * (1 - np.exp(-t / max(bloom, 1e-3))) * (0.8 + 0.2 * np.exp(-t / 0.6))
    w = 2 * np.pi * O.phase(f, n, sr)
    y = np.zeros(n)
    for k in range(1, K + 1):
        lo, hi = a0[k - 1], a1[k - 1]
        if max(lo, hi) > 1e-4:
            y += (lo + b * (hi - lo)) * np.sin(k * w)
    return apply(y, adsr(dur, attack, 0.15, sustain, release, sr, curve=1.5)) * (0.5 + 0.5 * vel)


def _air(n, sr, center, q, seed):
    return F.bandpass(O.white(n, seed=seed), center, sr, q)


VIOLIN_BODY = [(290, 60, 1.2), (480, 100, 1.5), (1100, 350, 0.8), (2500, 500, 1.0)]
CELLO_BODY = [(180, 40, 1.0), (300, 70, 1.4), (550, 150, 0.8), (1500, 400, 0.5)]


@instrument("violin", "Solo violin, bowed: singing tone with delayed vibrato (classical, folk fiddle, tango, film).",
            family="bowed", span=("G3", "C7"), attack=(0.07, "s; 0.02 = bitten accent, 0.2 = swell"), vibrato=(1.0, "0 = none .. 2 = wide"))
def violin(freq, dur, sr=DEFAULT_SR, vel=1.0, attack=0.07, vibrato=1.0):
    y = _blown(freq, dur, sr, vel, dict(tilt=1.7, formants=VIOLIN_BODY, corner=2000.0, slope=3.0),
               dict(tilt=1.1, formants=VIOLIN_BODY, corner=3000.0, slope=3.0),
               attack=attack, release=0.12, bloom=attack, vib=(5.8, 0.18 * vibrato, 0.12))
    n = y.shape[0]
    rosin = _air(n, sr, 2200, 1.0, 51) * 0.012 * np.minimum(1.0, np.abs(y) * 4)
    return (y + rosin) * 0.6


@instrument("cello", "Solo cello, bowed: dark, warm, vocal (laments, bass lines for chamber and film cues).",
            family="bowed", span=("C2", "C5"), attack=(0.1, "s"), vibrato=(1.0, "0 = none .. 2 = wide"))
def cello(freq, dur, sr=DEFAULT_SR, vel=1.0, attack=0.1, vibrato=1.0):
    y = _blown(freq, dur, sr, vel, dict(tilt=1.7, formants=CELLO_BODY, corner=1300.0, slope=3.0),
               dict(tilt=1.15, formants=CELLO_BODY, corner=1900.0, slope=3.0),
               attack=attack, release=0.15, bloom=attack, vib=(5.0, 0.15 * vibrato, 0.15), top=5000.0)
    n = y.shape[0]
    rosin = _air(n, sr, 1500, 1.0, 52) * 0.012 * np.minimum(1.0, np.abs(y) * 4)
    return (y + rosin) * 0.6


@instrument("clarinet", "Clarinet: hollow, woody, odd-harmonic tone (klezmer, jazz, classical, cartoons).",
            family="wind", span=("D3", "C6"))
def clarinet(freq, dur, sr=DEFAULT_SR, vel=1.0):
    even = _kt(freq, 0.08, 0.5)   # the upper register loses the hollow sound
    y = _blown(freq, dur, sr, vel, dict(tilt=1.7, even=even, corner=1500.0, slope=3.0),
               dict(tilt=1.2, even=even, formants=[(1500, 500, 0.5)], corner=2300.0, slope=3.0),
               attack=0.04, release=0.08, bloom=0.05, vib=(5.0, 0.03, 0.3))
    n = y.shape[0]
    return (y + _air(n, sr, _cut(freq, 3, 900, 2000), 1.5, 53) * 0.02 * np.abs(y)) * 0.6


@instrument("oboe", "Oboe: reedy, nasal, plaintive (pastoral, baroque, Middle-Eastern flavoured lines).",
            family="wind", span=("Bb3", "G6"))
def oboe(freq, dur, sr=DEFAULT_SR, vel=1.0):
    body = [(1150, 250, 2.5), (2700, 400, 0.8)]
    y = _blown(freq, dur, sr, vel, dict(tilt=1.1, formants=body, corner=2200.0, slope=3.5),
               dict(tilt=0.7, formants=body, corner=3000.0, slope=3.5),
               attack=0.03, release=0.08, bloom=0.04, vib=(5.5, 0.1, 0.25))
    return y * 0.55


@instrument("sax", "Saxophone (alto/tenor): breathy, husky, scoops into notes (jazz, soul, noir, 80s pop).",
            family="wind", span=("Bb2", "F5"), breath=(0.1, "air noise 0..1"), growl=(0.0, "0..1 rasp"))
def sax(freq, dur, sr=DEFAULT_SR, vel=1.0, breath=0.1, growl=0.0):
    body = [(550, 180, 1.2), (1300, 400, 1.0), (2300, 500, 0.4)]
    y = _blown(freq, dur, sr, vel, dict(tilt=1.5, formants=body, corner=1700.0, slope=3.0),
               dict(tilt=0.9, formants=body, corner=2600.0, slope=3.0),
               attack=0.035, release=0.1, bloom=0.07, vib=(5.0, 0.2, 0.2), scoop=0.5)
    n = y.shape[0]
    t = np.arange(n) / sr
    if growl > 0:
        y = y * (1 - 0.5 * growl * (1 + np.sin(2 * np.pi * 28 * t)) / 2)
    air = _air(n, sr, 1600, 0.8, 54) * breath * 0.25 * np.minimum(1.0, np.abs(y) * 3 + 0.2)
    return (y + apply(air, adsr(dur, 0.02, 0.1, 0.6, 0.1, sr))[:n]) * 0.6


TRUMPET_BODY = [(1200, 400, 1.2), (2300, 500, 0.6)]


@instrument("trumpet", "Solo trumpet: brightens as it is blown harder; `mute` gives the thin jazz harmon-mute tone (fanfares, mariachi, jazz, ska).",
            family="brass", span=("E3", "C6"), mute=(0.0, "0 = open .. 1 = harmon mute"))
def trumpet(freq, dur, sr=DEFAULT_SR, vel=1.0, mute=0.0):
    y = _blown(freq, dur, sr, vel, dict(tilt=2.2, formants=TRUMPET_BODY, corner=1800.0, slope=3.0),
               dict(tilt=0.9, formants=TRUMPET_BODY, corner=3200.0, slope=3.0),
               attack=0.03, release=0.08, bloom=0.05, vib=(5.5, 0.1, 0.3))
    if mute > 0:
        m = F.peak(F.highpass(y, 700, sr, order=2), 1800, sr, 1.5, 8.0)
        y = (1 - mute) * y + mute * F.lowpass(m, 3200, sr)
    return y * 0.6


@instrument("french_horn", "French horn: round, noble, distant (film scores, heroic themes, warm pads of brass).",
            family="brass", span=("C2", "F5"))
def french_horn(freq, dur, sr=DEFAULT_SR, vel=1.0):
    body = [(450, 150, 1.5)]
    return _blown(freq, dur, sr, vel, dict(tilt=2.6, formants=body, corner=1000.0, slope=3.0),
                  dict(tilt=1.6, formants=body, corner=1600.0, slope=3.0),
                  attack=0.08, release=0.15, bloom=0.1, vib=(5.0, 0.03, 0.4), top=4500.0) * 0.6


@instrument("trombone", "Trombone: broad, brassy low-mid voice (big band, ska, funeral marches, New Orleans).",
            family="brass", span=("E2", "C5"))
def trombone(freq, dur, sr=DEFAULT_SR, vel=1.0):
    body = [(520, 200, 1.2), (1500, 400, 0.4)]
    return _blown(freq, dur, sr, vel, dict(tilt=2.2, formants=body, corner=1400.0, slope=3.0),
                  dict(tilt=1.2, formants=body, corner=2300.0, slope=3.0),
                  attack=0.05, release=0.1, bloom=0.07, vib=(5.0, 0.05, 0.35), top=5000.0) * 0.6


@instrument("tuba", "Tuba: fat, puffing bottom of the brass band (oompah, polka, marches, circus).",
            family="brass", span=("C1", "C4"))
def tuba(freq, dur, sr=DEFAULT_SR, vel=1.0):
    body = [(230, 90, 1.2)]
    y = _blown(freq, dur, sr, vel, dict(tilt=2.6, formants=body, corner=600.0, slope=3.0),
               dict(tilt=1.7, formants=body, corner=950.0, slope=3.0),
               attack=0.05, release=0.1, bloom=0.06, vib=(5.0, 0.0, 0.5), top=3000.0)
    n = y.shape[0]
    puff = F.lowpass(O.white(n, seed=55), 400, sr) * decay_env(n, 0.03, sr) * 0.15 * vel
    return (y + puff) * 0.65


@instrument("harmonica", "Harmonica (blues harp): reedy, bends into notes, hand-cupped wah (blues, country, western).",
            family="wind", span=("C4", "C7"))
def harmonica(freq, dur, sr=DEFAULT_SR, vel=1.0):
    body = [(1300, 350, 1.5), (2500, 400, 0.6)]
    y = _blown(freq, dur, sr, vel, dict(tilt=1.3, formants=body, corner=2000.0, slope=3.0, even=0.9),
               dict(tilt=0.9, formants=body, corner=2800.0, slope=3.0, even=0.9),
               attack=0.03, release=0.08, bloom=0.05, vib=(5.5, 0.18, 0.25), scoop=0.6)
    n = y.shape[0]
    t = np.arange(n) / sr
    wah = 1 - 0.25 * np.clip((t - 0.25) / 0.3, 0, 1) * (1 + np.sin(2 * np.pi * 5.5 * t)) / 2
    return y * wah * 0.55


@instrument("pan_flute", "Pan flute / bamboo flute: breathy, chiffy, hollow (Andean, new age, calm exploration).",
            family="wind", span=("C4", "C7"), breath=(0.3, "air noise 0..1"))
def pan_flute(freq, dur, sr=DEFAULT_SR, vel=1.0, breath=0.3):
    rel = 0.15
    n = _n(dur, sr, rel)
    f = _vibrato(freq, n, sr, rate=4.5, depth=0.06, delay=0.3, ramp=0.4, scoop=0.4)
    amps = np.array([1.0, 0.06, 0.18, 0.02, 0.05]) * _roll(np.arange(1, 6) * freq, 2400.0) / float(_roll(freq, 2400.0))
    x = _harmonics(f, n, sr, amps)
    air = _air(n, sr, min(freq, 2400.0), 6.0, 56) * breath * 0.8 + _air(n, sr, 1600, 0.8, 57) * breath * 0.12 * _kt(freq, 1.0, 0.5)
    chiff = _air(n, sr, _cut(freq, 2, 800, 2400), 1.2, 58) * decay_env(n, 0.035, sr) * breath * 1.2
    return apply(x + air + chiff, adsr(dur, 0.05, 0.1, 0.8, rel, sr)) * 0.6 * (0.6 + 0.4 * vel)


@instrument("whistle", "Human whistle: pure tone with a little air, slides into each note (westerns, carefree tunes).",
            family="wind", span=("C5", "C7"))
def whistle(freq, dur, sr=DEFAULT_SR, vel=1.0):
    rel = 0.1
    n = _n(dur, sr, rel)
    f = _vibrato(freq, n, sr, rate=5.8, depth=0.12, delay=0.2, ramp=0.3, scoop=0.7)
    x = O.sine(f, n, sr) + 0.04 * O.sine(f * 2, n, sr)
    air = _air(n, sr, min(freq, 2600.0), 12.0, 59) * 0.35
    return apply(x + air, adsr(dur, 0.04, 0.1, 0.85, rel, sr)) * 0.6 * (0.6 + 0.4 * vel)


@instrument("ocarina", "Ocarina: round clay flute, almost a sine with a soft chiff (adventure themes, lullabies).",
            family="wind", span=("A4", "F6"), vibrato=(0.3, "0 = none .. 1 = wide"))
def ocarina(freq, dur, sr=DEFAULT_SR, vel=1.0, vibrato=0.3):
    rel = 0.1
    n = _n(dur, sr, rel)
    f = _vibrato(freq, n, sr, rate=5.2, depth=0.2 * vibrato, delay=0.2, ramp=0.3, scoop=0.25)
    amps = np.array([1.0, 0.05, 0.09]) * _roll(np.arange(1, 4) * freq, 2400.0) / float(_roll(freq, 2400.0))
    x = _harmonics(f, n, sr, amps)
    chiff = _air(n, sr, _cut(freq, 2, 800, 2200), 1.5, 60) * decay_env(n, 0.025, sr) * 0.25
    air = _air(n, sr, min(freq, 2400.0), 5.0, 61) * 0.06
    return apply(x + chiff + air, adsr(dur, 0.025, 0.1, 0.9, rel, sr)) * 0.6 * (0.6 + 0.4 * vel)


@instrument("didgeridoo", "Didgeridoo: low drone whose vowel slowly shifts (hold one long low note: C2-G2).",
            family="wind", span=("A1", "G2"), wow=(1.4, "vowel movement Hz"))
def didgeridoo(freq, dur, sr=DEFAULT_SR, vel=1.0, wow=1.4):
    rel = 0.2
    n = _n(dur, sr, rel)
    t = np.arange(n) / sr
    f = freq * (1 + 0.003 * np.sin(2 * np.pi * 0.7 * t))
    a0 = _spectrum(freq, sr, tilt=0.8, formants=[(350, 120, 2.5), (1100, 250, 1.0)], corner=1800.0, slope=3.0, top=4000.0)
    a1 = _spectrum(freq, sr, tilt=0.8, formants=[(650, 150, 2.5), (1700, 300, 1.2)], corner=1800.0, slope=3.0, top=4000.0)
    b = 0.5 + 0.5 * np.sin(2 * np.pi * wow * t)
    w = 2 * np.pi * O.phase(f, n, sr)
    y = np.zeros(n)
    for k in range(1, len(a0) + 1):
        y += (a0[k - 1] + b * (a1[k - 1] - a0[k - 1])) * np.sin(k * w)
    air = F.lowpass(O.white(n, seed=62), 1000, sr) * 0.05
    return apply(y + air, adsr(dur, 0.08, 0.1, 0.95, rel, sr)) * 0.6 * (0.6 + 0.4 * vel)

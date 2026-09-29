"""JSON sound spec renderer. A spec describes layers (synth notes, sequences, drums, sfx, files)
placed on a timeline, each with its own fx chain, plus a master fx chain.

Minimal spec:   {"out": "beep.wav", "layers": [{"type": "sfx", "kind": "beep"}]}
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import drums as D
from . import fx as FX
from . import instruments as I
from . import sfx as S
from . import speech as SPK
from .core import DEFAULT_SR, declick, mix, normalize, read_wav, resample, samples, silence, trim_tail, write_wav
from .notes import parse_pitch_list, parse_sequence


class SpecError(ValueError):
    pass


def _params(layer: dict) -> dict:
    p = dict(layer.get("params") or {})
    return p


def _fx(x: np.ndarray, chain, sr: int) -> np.ndarray:
    if not chain:
        return x
    return FX.apply_chain(x, chain, sr)


def render_layer(layer: dict, sr: int) -> tuple[np.ndarray, float]:
    """Returns (signal, start_seconds)."""
    kind = layer.get("type")
    at = float(layer.get("at", 0.0))
    gain = float(layer.get("gain", 1.0))
    vel = float(layer.get("vel", 1.0))

    if kind in ("synth", "note", "notes"):
        inst = layer.get("inst", "synth")
        notes = layer.get("notes", layer.get("note", "C4"))
        freqs = parse_pitch_list(notes)
        dur = float(layer.get("dur", 0.5))
        strum = float(layer.get("strum", 0.0))
        y = I.render_chord(inst, freqs, dur, sr, vel, strum=strum, **_params(layer))

    elif kind in ("seq", "sequence", "melody"):
        y = render_sequence(layer, sr)

    elif kind == "drum":
        y = D.render_drum(layer.get("kind", "kick"), sr, vel, **_params(layer))

    elif kind == "pattern":
        # drum pattern: {"type":"pattern","kind":"hihat","hits":[0,0.25,0.5],"params":{}} or "steps":"x-x-x-x-" with "step":0.125
        one = D.render_drum(layer.get("kind", "kick"), sr, vel, **_params(layer))
        hits = layer.get("hits")
        if hits is None and "steps" in layer:
            step = float(layer.get("step", 0.125))
            hits = [i * step for i, ch in enumerate(layer["steps"]) if ch.lower() == "x"]
        y = mix([(one, float(t)) for t in (hits or [0.0])], sr)

    elif kind == "sfx":
        y = S.render_sfx(layer.get("kind", "beep"), sr, **_params(layer))

    elif kind in ("speech", "say", "voice"):
        y = SPK.render_speech(layer.get("text"), sr, phonemes=layer.get("phonemes"), **_params(layer))

    elif kind in ("file", "sample"):
        y, fsr = read_wav(layer["path"])
        y = resample(y, fsr, sr)

    elif kind == "silence":
        y = silence(float(layer.get("dur", 0.5)), sr)

    elif kind == "group":
        y = render_layers(layer.get("layers", []), sr)

    else:
        raise SpecError(f"unknown layer type {kind!r} (synth|seq|drum|pattern|sfx|speech|file|silence|group)")

    if "repeat" in layer:
        reps = int(layer["repeat"])
        every = float(layer.get("every", y.shape[0] / sr))
        y = mix([(y, i * every) for i in range(reps)], sr)

    y = _fx(y, layer.get("fx"), sr)
    return y * gain, at


def render_sequence(layer: dict, sr: int) -> np.ndarray:
    inst = layer.get("inst", "pluck")
    steps = layer.get("steps", layer.get("notes", "C4 E4 G4"))
    default_dur = float(layer.get("step", 0.25))
    if isinstance(steps, str):
        steps = parse_sequence(steps, default_dur)
    else:
        norm = []
        for s in steps:
            if isinstance(s, str):
                norm.extend(parse_sequence(s, default_dur))
            else:
                pitches = s.get("notes", s.get("note", s.get("pitches", [])))
                pitches = parse_pitch_list(pitches) if pitches not in ([], None, "-") else []
                norm.append({"pitches": pitches, "dur": float(s.get("dur", default_dur)), "vel": float(s.get("vel", 1.0))})
        steps = norm
    legato = float(layer.get("legato", 1.0))
    gap = float(layer.get("gap", 0.0))
    strum = float(layer.get("strum", 0.0))
    vel = float(layer.get("vel", 1.0))
    params = _params(layer)
    transpose = float(layer.get("transpose", 0))
    parts = []
    t = 0.0
    for st in steps:
        if st["pitches"]:
            freqs = [f * 2 ** (transpose / 12) for f in st["pitches"]]
            y = I.render_chord(inst, freqs, st["dur"] * legato, sr, vel * st["vel"], strum=strum, **params)
            parts.append((y, t))
        t += st["dur"] + gap
    if not parts:
        return silence(t or 0.1, sr)
    return mix(parts, sr)


def render_layers(layers: list[dict], sr: int) -> np.ndarray:
    parts = [render_layer(l, sr) for l in layers]
    return mix(parts, sr)


def render_spec(spec: dict, sr: int | None = None) -> tuple[np.ndarray, int]:
    sr = int(sr or spec.get("sr", DEFAULT_SR))
    layers = spec.get("layers")
    if layers is None:
        # allow a bare single layer spec: {"type": "sfx", "kind": "beep", "out": ...}
        if "type" in spec:
            layers = [spec]
        else:
            raise SpecError("spec needs a 'layers' list (or be a single layer with 'type')")
    y = render_layers(layers, sr)
    y = _fx(y, spec.get("fx"), sr)
    if spec.get("duration"):
        n = samples(float(spec["duration"]), sr)
        if y.shape[0] > n:
            y = y[:n]
        else:
            from .core import pad_to
            y = pad_to(y, n)
    loop = spec.get("loop")
    if loop:
        # Loopable output: crossfade tail into head; trim/declick would break the seam.
        from .fx import loop as _loop
        y = _loop(y, sr, crossfade=float(loop) if not isinstance(loop, bool) else 0.05)
    else:
        if spec.get("trim", True):
            y = trim_tail(y, sr=sr)
        if spec.get("declick", True):
            y = declick(y, sr)
    lvl = spec.get("normalize", -1.0)
    if lvl is not None and lvl is not False:
        y = normalize(y, float(lvl))
    y = y * float(spec.get("gain", 1.0))
    return np.clip(y, -1, 1), sr


def render_to_file(spec: dict, out: str | Path | None = None, out_dir: str | Path | None = None, sr: int | None = None) -> Path:
    y, sr = render_spec(spec, sr)
    path = Path(out or spec.get("out") or "out.wav")
    if out_dir and not path.is_absolute():
        path = Path(out_dir) / path
    return write_wav(path, y, sr, bits=int(spec.get("bits", 16)))


def load_specs(source: str | Path | dict | list) -> list[dict]:
    """Accepts a path, a JSON string, a dict, or a list. Returns a list of sound specs.
    Batch files may be {"sounds": [...], "out_dir": "..."} or a plain list."""
    if isinstance(source, (str, Path)):
        s = str(source)
        if s.strip().startswith(("{", "[")):
            data = json.loads(s)
        else:
            data = json.loads(Path(s).read_text(encoding="utf-8"))
    else:
        data = source
    if isinstance(data, list):
        return data
    if "sounds" in data:
        out_dir = data.get("out_dir")
        specs = []
        for sp in data["sounds"]:
            sp = dict(sp)
            for k in ("sr", "fx", "normalize"):
                if k in data and k not in sp:
                    sp[k] = data[k]
            if out_dir and "out" in sp and not Path(sp["out"]).is_absolute():
                sp["out"] = str(Path(out_dir) / sp["out"])
            specs.append(sp)
        return specs
    return [data]


EXAMPLE = {
    "out": "sounds/example_stinger.wav",
    "sr": 44100,
    "layers": [
        {"type": "seq", "inst": "bell", "steps": "C5:0.12 E5:0.12 G5:0.12 C6:0.5", "gain": 0.8,
         "fx": [{"type": "delay", "time": 0.18, "feedback": 0.3, "mix": 0.25}]},
        {"type": "synth", "inst": "pad", "notes": "C4:maj", "dur": 0.9, "at": 0.0, "gain": 0.5},
        {"type": "drum", "kind": "kick", "at": 0.0, "gain": 0.7},
        {"type": "sfx", "kind": "whoosh", "at": 0.3, "params": {"dur": 0.4}, "gain": 0.4},
    ],
    "fx": [{"type": "reverb", "mix": 0.25, "size": 0.6}, {"type": "compressor"}],
    "normalize": -1.0,
}

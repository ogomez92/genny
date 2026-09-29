---
name: genny
description: Generate game sounds as .wav files with the genny CLI from a free-form request, e.g. "/genny 10 notification sounds", "/genny bell + hit", "/genny cat meows and is thrown in a blender". Use whenever the user wants sound effects, UI sounds, jingles, stingers, drums, instrument samples, short spoken words/letters/numbers, or any audio for a game or app.
---

# genny — make sounds from a one-line request

`genny` synthesizes sounds offline (instruments, drums, sfx, effects) into WAV files from JSON specs. You are the sound designer: turn the request into specs, render them, report the files. Do not ask clarifying questions; make reasonable choices and say what you chose.

## 0. Check the tool

```
genny --version
```
If it is missing: `uv tool install --editable /home/genny` (the repo lives there; `AGENTS.md` in it is the full manual). If uv fails with `os error 448` ("untrusted mount point") on a managed Python, add `--python "C:\Program Files\Python314\python.exe"` to use the system Python instead.

## 1. Read the manual (once per session)

Read `reference.md` next to this file. It documents the spec format, note/step notation, every layer type, and design recipes. Then run `genny list --json` and keep the output in mind: it is the exact catalog of instruments, drums, sfx, effects and their parameters. Unknown names or params are rejected, so stick to the catalog.

## 2. Interpret the request

- **"N <category> sounds"** → N distinct sounds in that category. Vary instrument, pitch, contour (rising/falling), length and effects; no near-duplicates. Default count is 1 for a singular request, 5 for a plural one without a number.
- **"A + B"** → one sound that layers A and B (e.g. `bell + hit` = a bell note layer plus a `hit` sfx layer, timed together). Render 2–3 variations unless told otherwise.
- **Imaginative / descriptive requests** ("cat meows and is thrown in a blender", "haunted elevator ding") → decompose the scene into stages on the timeline and build each stage from primitives:
  - spoken words / letters / numbers / announcer callouts ("G", "fuel low", "level up!", "tres"): a `speech` layer (`{"type": "speech", "text": "fuel low", "params": {"voice": "female"}}`, `lang: "es"` for Spanish; character voices `robot`, `android`, `synth`, `bad_robot`, `evil_robot`, `monster`, `giant`, `alien`, `ghost`; set `pitch` in Hz with the suffix, `"90hz"`, since a bare number is a MIDI note); `genny say "text" --show` prints the phonemes; see the Speech section of `reference.md`
  - voices/animals: `flute`/`choir`/`synth` with `vibrato`, `tone` with pitch sweeps via `sweep_up`/`sweep_down`, `pitch`, `ringmod` for weirdness
  - vehicles: `car_engine` (realistic, rpm/load/cylinders; render an rpm bank and crossfade at runtime — see reference)
  - machines: `engine`, `tone` with `saw`, `distortion`, `ringmod`, `tremolo`, `bitcrush`
  - impacts/violence: `hit`, `punch`, `explosion`, `glitch`, `stutter`, `speed` (tape stop), `reverse`
  - space/place: `reverb` size, `muffle`, `telephone`, `underwater`, `delay`
  Use `at` offsets so the story reads left to right. Aim for 1–4 s total.
- **Style words**: "retro/8-bit" → `chip`, `chiptri`, `bitcrush`; "cinematic" → `taiko`, `strings`, `choir`, big `reverb`; "soft/subtle" → `sine`, `glass`, `marimba`, low `vel`, small reverb; "harsh" → `distortion`, `square`, `alarm`, `error`.

## 3. Write a batch and render it

Put everything in one batch file under `sounds/<slug>/` in the current working directory (or wherever the user said), with descriptive file names:

```json
{
  "out_dir": "sounds/notifications",
  "sounds": [
    {"out": "chime_two_up.wav", "layers": [{"type": "seq", "inst": "bell", "steps": "G5:0.12 C6:0.4"}],
     "fx": [{"type": "reverb", "mix": 0.2, "size": 0.4}]}
  ]
}
```

```
genny render sounds/notifications/batch.json --quiet
```

Read the final `N rendered, M failed` line. Fix every `ERROR in spec #i` (usually a bad param name; check `genny list`) and re-render. Keep the batch JSON next to the WAVs so the user can tweak and re-run.

## 4. Report

List the files with one short phrase each describing the sound and how to vary it (which param to change). Mention `genny play <file>` to audition and `genny render <batch.json>` to re-render after edits. Keep the report short.

## Quality rules

- Notifications/UI: 0.05–0.6 s, pitched C5–C7, normalize -1 dB. Game-over/win stingers: 1–4 s. Never exceed ~6 s unless asked.
- Layer 2–4 things (body + transient + tail) rather than one raw oscillator.
- Add a small `reverb` to anything melodic; leave pure UI clicks/blips dry.
- Do not ask questions before rendering. Render first, then offer variations.

## Sounds for games (runtime cues)

When the sounds feed a game engine that loops/positions them (the user's audio games):
- **Loops that mark a place must pulse fast**: ≤ ~0.5 s between onsets (a spoken beacon letter back to back, a cone "bloop bloop" every 0.4 s). A player can't steer toward something heard every 1.5 s.
- **Several of one kind will overlap**: plan per-instance pitch offsets (render variants or pitch at runtime, a few semitones apart) so they don't merge into one voice.
- **Positional cues**: mono (reverb/chorus/pan make stereo — add `{"type": "mono"}`), with a bright layer above ~2 kHz (`static` white → `highpass` 1800 → `bandpass` ~3000) so binaural can place them.
- **Never piercing**: the player's own continuous bed (engine, wind, wheels) keeps nothing above ~2.5 kHz (`car_engine` with `bright` 0); harsh/raspy timbre reads as "too loud" long before level does. UI/pickups: marimba/kalimba ≤ C6, lowpass ≤ 4 kHz.
- **Objects must sound like the object** (a fuel can = metal tonk + slosh + glug, not a drone) — foley from shaped noise, tones only for abstract signals.
- **Informational speech** (scores, countdowns, menus) usually belongs to the game's screen reader; render speech only for voices that must come *from somewhere* in the world or are part of the sound design.

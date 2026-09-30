# genny — agent guide

`genny` is a CLI that synthesizes game sounds (instruments, drums, sound effects, effects chains) into `.wav` files. It is deterministic, has no external audio dependencies, and is meant to be driven by an AI agent that writes JSON specs.

**Read this file top to bottom once, then use `genny list --json` for the exact, current catalog of names and parameters. The catalog is the source of truth; this file explains how to combine things.**

## Setup / invocation

```
uv tool install --editable <path-to-genny>   # then: genny ...
# or, from the repo:
uv run genny ...
```

Every command writes a WAV and prints `wrote <path> (<seconds>, mono|stereo, <sr> Hz)`. Non-zero exit on error with `error: ...` on stderr. Unknown instrument/effect/param names are rejected with the allowed list, so failures are cheap to fix.

## Two ways to talk to genny

1. **Quick one-shots** on the command line (`synth`, `seq`, `drum`, `sfx`, `say`, `fx`).
2. **JSON specs** via `genny render` — the main interface for anything layered or for batches. Prefer this when making more than one sound.

### One-shots

```
genny synth <inst> "<notes>" [--dur S] [--vel 0..1] [--strum S] [-p k=v ...] [--fx NAME:k=v,k=v ...] -o out.wav
genny seq   <inst> "<steps>" [--step S] [--legato F] [--gap S] [--transpose N] [-p ...] [--fx ...] -o out.wav
genny drum  <kind> [-p k=v ...] [--fx ...] -o out.wav
genny sfx   <kind> [-p k=v ...] [--fx ...] -o out.wav
genny say   "<text>" [--phonemes] [--show] [-p k=v ...] [--fx ...] -o out.wav   # speech (see "Speech")
genny fx    in.wav --fx NAME[:k=v,...] [--fx ...] -o out.wav      # process an existing file
genny render spec.json [more.json ...] [--out-dir DIR] [--quiet]   # or:  genny render --json '{...}'   or:  ... | genny render -
genny list [instruments|drums|sfx|fx|speech|phonemes|words|waves|scales|chords] [--json]
genny info file.wav ...      # duration / peak / rms
genny play file.wav ...      # audition through the system player
genny example                # prints a full example spec
```

Examples:

```
genny sfx beep -p freq=880 -p dur=0.1 -o ui/beep.wav
genny sfx proximity -p rate=8 -p dur=1 -o ui/wall_close.wav
genny synth bell "C6" --dur 0.3 -p ratio=5.04 --fx reverb:mix=0.3 -o notif/ding.wav
genny seq brass "C4:0.15 E4:0.15 G4:0.15 C5:0.6" --fx reverb:mix=0.25,size=0.7 -o win/fanfare.wav
genny drum kick -p tune=48 -p decay=0.6 -o drums/kick.wav
genny fx voice.wav --fx telephone --fx reverb:mix=0.1 -o voice_radio.wav
```

## Pitch notation

Two kinds of pitch input:

- **Frequency parameters** (`freq`, `freq2` on sfx such as `tone`/`beep`/`alarm`, speech `pitch`): **a number is always Hz** — `"freq": 55` is a 55 Hz hum. `"110hz"`, `"110"` and a note name (`"A2"`) also work.
- **Notes** (`notes` in synth layers, `steps` in seq layers, `genny synth`/`seq` arguments): `C4`, `F#3`, `Bb2`, a MIDI number `60`, or Hz `440hz` / `440.0`. Here a bare integer 0–127 is a MIDI note (musical context); write Hz with the suffix.

Multiple notes: `"C4 E4 G4"` or `"C4,E4,G4"`. Named chord: `"C4:maj"` (chords: `genny list chords` → maj min dim aug sus2 sus4 maj7 min7 dom7 add9 power maj9 min9 oct).

## Step notation (melodies / stingers)

Whitespace-separated tokens for `seq`:

| token | meaning |
|---|---|
| `C5` | note with default step duration (`--step`, default 0.25 s) |
| `C5:0.12` | note lasting 0.12 s |
| `[C5,E5,G5]:0.5` | chord for 0.5 s |
| `C5:maj:0.5` | named chord for 0.5 s |
| `-:0.1` | rest for 0.1 s |
| `C5:0.2@0.6` | velocity 0.6 (softer, usually darker) |

Instruments add their own release/ring after each note, so notes overlap naturally. `legato` < 1 shortens the sounding part of each step (staccato); `gap` adds silence between steps.

## JSON spec format

```jsonc
{
  "out": "sounds/win/fanfare_01.wav",   // output path (relative to --out-dir if given)
  "sr": 44100,                          // optional
  "duration": 1.5,                      // optional hard length (pads or cuts)
  "layers": [ ...layer objects... ],    // mixed together on one timeline
  "fx": [ {"type": "reverb", "mix": 0.2}, {"type": "compressor"} ],   // master chain, in order
  "normalize": -1.0,                    // peak dB after fx; null to skip
  "gain": 1.0,
  "trim": true,                         // drop silent tail
  "declick": true
}
```

### Layer objects

Common keys for every layer: `"at"` (start seconds, default 0), `"gain"` (linear, default 1), `"fx"` (effects chain applied to just this layer), `"repeat"` + `"every"` (repeat the layer N times every X seconds).

```jsonc
{"type": "synth", "inst": "bell", "notes": "C5 E5 G5", "dur": 0.4, "vel": 0.8, "strum": 0.03, "params": {"ratio": 3.5}}
{"type": "seq",   "inst": "pluck", "steps": "C4:0.1 E4:0.1 G4:0.3", "step": 0.25, "legato": 1.0, "gap": 0, "transpose": 0, "vel": 1, "params": {}}
{"type": "seq",   "inst": "piano", "steps": [{"note": "C4", "dur": 0.2}, {"notes": ["E4", "G4"], "dur": 0.4, "vel": 0.7}, {"note": "-", "dur": 0.1}]}
{"type": "drum",  "kind": "kick", "vel": 1.0, "params": {"tune": 50}}
{"type": "pattern", "kind": "hihat", "steps": "x-x-xxx-", "step": 0.125}      // or "hits": [0, 0.5, 0.75]
{"type": "sfx",   "kind": "whoosh", "params": {"dur": 0.4, "direction": "down"}}
{"type": "speech", "text": "fuel low", "params": {"voice": "female"}}          // spoken words (see "Speech")
{"type": "file",  "path": "existing.wav"}                                      // import a sample
{"type": "silence", "dur": 0.5}
{"type": "group", "layers": [ ... ], "fx": [ ... ]}                              // sub-mix with its own fx
```

`params` must only contain keys the instrument/drum/sfx/speech declares (see `genny list --json`). Anything else is an error.

### Batches

```jsonc
{
  "out_dir": "sounds/notifications",     // prefixed to each relative "out"
  "fx": [{"type": "compressor"}],         // defaults inherited by sounds that don't set their own
  "sounds": [ { ...spec... }, { ...spec... } ]
}
```
A top-level JSON array of specs also works. `genny render batch.json` renders all, reports `N rendered, M failed`, and continues past errors unless `--strict`.

## Catalog overview (run `genny list` for parameters)

**Instruments** (`synth`/`seq` layers). Each note = `inst(freq, dur)`, returns note plus release.
- Keys/mallets: `piano`, `epiano`, `marimba`, `vibraphone`, `kalimba`, `music_box`, `steel_drum`, `glass`, `bell`
- Plucked: `pluck`, `harp`, `guitar`
- Bass: `bass`, `sub`, `wobble`
- Leads/pads: `lead`, `pad`, `strings`, `brass`, `organ`, `flute`, `choir`, `pwm`
- Retro: `chip` (pulse; `width` 0.125/0.25/0.5), `chiptri`, `board` (80s pinball/arcade sound-board voice: gritty pulse with an onset pitch blip)
- Raw: `sine`, `square`, `saw`, `synth` (generic: `wave`, ADSR, `cutoff`, `res`, `fenv`, fm `ratio`/`index`)

**Drums**: `kick`, `kick808`, `snare`, `clap`, `hihat`, `openhat`, `tom`, `rim`, `cowbell`, `crash`, `ride`, `shaker`, `tambourine`, `woodblock`, `taiko`, `zap_kick`.

**SFX**: `beep`, `blip`, `click`, `pop`, `coin`, `powerup`, `powerdown`, `laser`, `zap`, `hit`, `punch`, `explosion`, `jump`, `whoosh`, `swoosh`, `alarm`, `siren`, `error`, `success`, `proximity`, `radar`, `riser`, `sweep_up`, `sweep_down`, `bubble`, `glitch`, `static`, `wind`, `thunder`, `footstep`, `door`, `engine`, `car_engine`, `magic`, `heartbeat`, `tone`, `noise`, `typewriter`, `countdown`; pinball/mechanical: `solenoid`, `flipper`, `pop_bumper`, `slingshot`, `knocker`, `steel_ball`, `ball_roll`, `spinner`, `spring`, `chirp` (see "Pinball / mechanical foley").

**Speech**: `speech` layer / `genny say` — formant voice for letters, numbers and short game words; voices `male`, `female`, `child`, `whisper`, plus character voices `robot`, `android`, `synth`, `bad_robot`, `evil_robot`, `monster`, `giant`, `alien`, `ghost`; English + Spanish (`lang=es`). See "Speech" below.

**Effects** (`"fx"` chains; also `--fx name:k=v,k=v`):
- Space: `reverb` (mix,size,damp,predelay,width), `delay` (time,feedback,mix,pingpong), `chorus`, `flanger`, `phaser`, `width`, `pan`, `autopan`
- Tone: `lowpass`, `highpass`, `bandpass`, `notch`, `eq`, `lowshelf`, `highshelf`, `sweep` (moving filter), `muffle` (through a wall), `telephone`, `underwater`
- Character: `distortion`, `bitcrush`, `ringmod`, `vibrato`, `tremolo`, `stutter`, `pitch` (semitones, same length), `speed` (tape speed), `reverse`
- Dynamics/utility: `compressor`, `limiter`, `gain`, `normalize`, `fade` (in,out), `trim`, `mono`

`reverb`, `chorus`, `pan`, `autopan`, `width`, and `delay pingpong` produce stereo files; everything else keeps the channel count.

## Speech (spoken letters, numbers, short words)

A built-in Klatt-style formant synthesizer (no models, no downloads) for short spoken cues: letter names, numbers, and short game words/phrases ("fuel low", "level up", "game over"). English by default; Spanish with `lang=es`.

```
genny say "G" -o say/g.wav
genny say "fuel low" -p voice=female -o say/fuel_low.wav
genny say "G" -p lang=es -o say/g_es.wav                      # "ge" /xe/
genny say "level up!" --show -o say/level_up.wav               # --show prints the phonemes it used
genny say "JH IY1" --phonemes -o say/g_raw.wav                 # raw ARPAbet
```

Layer (all common layer keys work: `at`, `gain`, `fx`, `repeat`/`every`):

```jsonc
{"type": "speech", "text": "fuel low", "params": {"voice": "female", "rate": 1.1}}
{"type": "speech", "text": "S", "params": {"lang": "es"}}          // "ese"
{"type": "speech", "phonemes": "F Y UW1 AH0 L | L OW1"}            // raw ARPAbet, "|" = word break, "_" = short pause
{"type": "speech", "text": "go /G OW1/ now"}                       // /slashes/ inside text = raw phonemes
```

Params (`genny list speech`):

| param | default | meaning |
|---|---|---|
| `voice` | `male` | `male`, `female`, `child`, `whisper` (unvoiced); robots/creatures: `robot` (monotone + ring-mod), `android` (clean, snapped pitch, faint ring + chorus), `synth` (vocoder-style saw carrier, semitone-snapped), `bad_robot` (bit-crushed, stutters/dropouts/pitch hiccups), `evil_robot` (very low, octave-down sub, slow ring, overdrive), `monster` (huge tract, growl, distortion), `giant` (big slow natural), `alien` (tiny tract, high, warbling ring), `ghost` (swimming whisper) |
| `pitch` | from voice | base F0 in Hz or a note name (male 115, female 205, child 280, robot 100, evil_robot 62, monster 58, alien 240); every preset still takes `pitch`/`formant_shift`/`rate` overrides |
| `rate` | 1.0 | speed multiplier |
| `formant_shift` | from voice | vocal-tract size: 0.85 = big/deep, 1.16 female, 1.28 child |
| `breath` | from voice | breathiness 0..1 |
| `vibrato` | 0 | depth in semitones |
| `intonation` | `auto` | `statement` (falling), `question` (rising), `exclaim`, `flat`; `auto` follows a final `?`/`!` |
| `emphasis` | 1.0 | pitch-accent strength |
| `lang` | `en` | `en` or `es` |
| `gap` | 0 | extra seconds between words (countdowns, spelling) |
| `seed` | 0 | tiny jitter/noise variation between takes |

Text handling: a lone letter (or an all-caps token of 2–5 letters not in the dictionary, e.g. `GPS`) is spoken as letter names; digits become number words (`21` → "twenty one"; Spanish "veintiuno"); `,` `.` `!` `?` split phrases with a pause. English words come from a built-in dictionary (`genny list words`: numbers, letters and ~250 common game words — go, ready, level, up, fuel, low, bomb, shield, magnet, turbo, time, game, over, perfect, combo, bonus, score, win, lose, danger, warning, coin, lap, left, right...) with a rough letter-to-sound fallback for anything else — check odd words with `--show` and pass phonemes if it guesses wrong. Spanish uses spelling rules (Castilian: `z`/`ce`/`ci` = TH, `j`/`ge` = X, `r` tap / `rr` trill, stress from accents and the penultimate rule), so any Spanish word works.

Phonemes (`genny list phonemes`), ARPAbet with stress digit on vowels (1 primary, 2 secondary, 0 unstressed):
- vowels `IY IH EH AE AA AO UH UW AH AX IX ER AXR`, diphthongs `EY AY OY AW OW`, Spanish pure vowels `A E I O U`
- stops `P B T D K G`, fricatives `F V TH DH S Z SH ZH HH X` (X = Spanish jota), affricates `CH JH`
- nasals `M N NG`, liquids/glides `L R W Y`, flap/tap `DX`, trill `RR`

Tips:
- Output is dry mono; `normalize: -3` is a good level. A touch of `reverb` (mix 0.08–0.15, size 0.3) makes it sit in a mix; `telephone` (+ `distortion` light) = radio/announcer; `voice: robot`/`android`/`synth` = computer, `bad_robot` = broken machine, `evil_robot`/`monster` = villain/boss, `alien`/`ghost` = otherworldly (character voices are mono and dry — add fx on top); `pitch` + `formant_shift` 0.85 = giant/boss voice.
- Keep utterances short (1–4 words). It is intelligible but clearly synthetic; single letters and numbers are the strongest, long sentences the weakest.
- Weakest sounds: `TH`/`DH`/`F`/`V` (quiet, easily confused), `NG`, and the letter-to-sound fallback for unknown English words.

## Pinball / mechanical foley

Real machines are mechanism, not music: build them from these instead of `bell`/`glass`/`marimba` (tonal mallets make a table sound like a bell tree). Each is a short noise transient + inharmonic steel modes that die in tens of ms + a wooden-cabinet thump.

- `solenoid` — any coil or relay: `size` 0 (relay/switch tick) .. 1 (big coil), `metal` ring, `thump` cabinet thud, `bounce` armature rebound (the "ka-chak"). Use size 0 for menu ticks and switch hits.
- `flipper` (`force`, `buzz` AC coil hum), `pop_bumper` (`tone` 0.6..1.6 tells bumpers apart), `slingshot` (`tone`), `knocker` (the replay/extra-ball BANG; `size`, `rattle`).
- `steel_ball` — ball impact, `surface` metal (rail/post clank) | wood (tock) | rubber (thup) | plastic (target/ramp clack), `force` 0..1.
- `ball_roll` — steel ball on a wooden playfield, `speed` 0..1; loop it with `"loop": 0.3`.
- `spinner` — one flap tick per pass (`spins` > 1 = a decelerating whirr); `spring` — plunger, `action` pull (creak tick) | release (rod slam + boing), `tension`.
- Solid-state sound board (80s pinball/arcade speaker): `chirp` sfx (pitch sweep with `warble` LFO, `steps` for stepped bip-bips, `bits` DAC grit) and the `board` instrument (gritty pulse with a pitch blip on every note) for score blips and jingles; `chiptri` makes the bass. Recipe: foley layer + one short `chirp`/`board` blip = a scoring hit (e.g. `pop_bumper` + square `chirp` 980→330 Hz 0.07 s `bits` 5 at gain 0.3).

## Design recipes (what tends to sound right)

- **UI / notification**: short (0.1–0.6 s), high-ish (C5–C7), `bell`/`glass`/`marimba`/`sine`, a small `reverb` (mix 0.15–0.3, size 0.3–0.5). Two rising notes = positive, two falling = negative. Keep `normalize` at -1 to -3 dB.
- **Wall proximity / radar**: `sfx proximity` with `rate` 2 (far) → 12 (close); or a `beep` layer with `repeat`/`every`.
- **Stingers**: `seq` 3–6 notes, 0.08–0.15 s each, ending on a longer note or chord; layer a `pad`/`strings` chord underneath at `gain` 0.4–0.6; master `reverb` mix 0.2–0.35.
- **Win / fanfare**: `brass` or `lead` arpeggio up a major triad ending on the octave chord; add `crash` or `taiko` at `at: 0`; `chip`+`bitcrush` for retro.
- **Game over**: descending minor line (`piano`, `chip`, `organ`), slow `pad` minor chord, `powerdown` sfx, `taiko`/`kick808`; darken with `lowpass` 1500–3000 or `muffle`; long `reverb` (size 0.8).
- **Impacts**: `hit`/`punch`/`explosion` + `kick` layer for weight; `distortion` for crunch; `lowpass` sweep for distance.
- **Layering rule of thumb**: 2–4 layers; one body (low), one transient (click/noise), one tail (reverb/pad). Sum gains ≈ 1–1.5, normalize handles the rest.
- **Variations**: change `vel`, `transpose`, `params.decay`, effect `mix`, or the note set. Same spec with a different `seed`-free variation still renders identically, so name files by intent (`ui_confirm_soft.wav`).

## Typical agent workflow

1. `genny list --json` once, cache it.
2. Write one batch JSON per folder/category with descriptive `out` names.
3. `genny render batch.json --quiet`; read the `N rendered, M failed` line and fix any `ERROR in spec #i` lines.
4. `genny info` on outputs if you need to verify durations/levels. `genny play` to audition (blocks until done).

## Vehicle engines (`car_engine`)

`{"type": "sfx", "kind": "car_engine", "params": {"rpm": 3000, "load": 0.6}}` is a physically-modelled combustion engine: per-cylinder firing pulses (4-stroke, fixed per-cylinder strength = the lope), exhaust pipe comb + body resonances + muffler lowpass that opens with `load`, a low exhaust burble and intake breath modulated by the firing. Params: `rpm` (crank speed), `cylinders` (4), `load` 0..1 (throttle: brighter, more intake), `rough` 0..1 (uneven firing, jitter, misfires), `pipe` (exhaust delay s, longer = throatier), `body` 0..1, `bright` 0..1 (0 = road car from the cabin, nothing above ~2.5 kHz; raise for an open sporty exhaust with combustion rasp), `seed` (engine character), `dur`. Keep `bright` at 0 for the player's own car: sharp/raspy engine timbres read as piercing and "too loud" long before their level is.

- **Engine bank for a player car:** render 4–6 loops at fixed rpm (e.g. 1100, 2000, 3000, 4200, 5600; `"loop": 0.3`, `duration` 3.3) and at runtime equal-power crossfade the two nearest, each played at `rate = rpm / renderedRpm`. One sample pitched across the whole range sounds like a tape speeding up.
- **Ignition / stall:** chain short `car_engine` layers — cranking is `rpm` 220–300 with `rough` 0.9 and a starter-motor `synth` saw with tremolo; a catch is a burst at 2300–2600 then settling to idle; a stall is 1100 → 700 → 420 with fades.
- The generic `engine` sfx is a simple saw hum; prefer `car_engine` for anything the player drives.

## Loops (for runtime engines that loop a sample)

Set `"loop": true` (or `"loop": 0.08` for a custom crossfade in seconds) at the top level of a spec. The last `crossfade` seconds are blended into the start with an equal-power crossfade and cut off, so playing the file with `loop=true` in a game engine has no click or gap. `trim`/`declick` are skipped for loop specs (they would break the seam). Use a `duration` long enough to hide the repetition (2–6 s for drones, wind, engines). The same thing is available as an effect: `{"type": "loop", "crossfade": 0.05}`.

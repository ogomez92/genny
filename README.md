# genny

Procedural sound generator CLI for games. Synthesized instruments, drums, sound effects, a physically-modelled car engine (`car_engine`), a small formant speech synthesizer (letters, numbers, short words; English + Spanish; human, robot, android, synth, bad/evil robot, monster, giant, alien and ghost voices) and an effects rack, all rendered offline to WAV from a JSON spec or a one-line command. Built to be driven by AI agents (see `AGENTS.md`).

```
uv tool install --editable .      # installs the `genny` command
genny sfx coin -o coin.wav
genny seq bell "C5:0.1 E5:0.1 G5:0.1 C6:0.5" --fx reverb:mix=0.3 -o stinger.wav
genny say "level up!" -p voice=female -o level_up.wav
genny say "surrender" -p voice=evil_robot -o boss.wav
genny sfx car_engine -p rpm=3000 -p load=0.6 -o engine.wav
genny render examples/library/win.json
genny list
```

- `AGENTS.md` — the full spec format, notation and recipes (written for AI agents, works for humans too).
- `examples/library/*.json` — demo batch files (25 sounds each); renders go to `sounds/` (not committed).
- `examples/build_library.py` — regenerates those batch files and renders them.
- `skill/genny/` — a Claude Code skill (`SKILL.md` + `reference.md`): `cp -r skill/genny ~/.claude/skills/genny` to get `/genny ...`.

Python 3.10+, numpy, scipy. No other dependencies.

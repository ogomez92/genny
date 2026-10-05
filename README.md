# genny

Procedural sound and music generator CLI for games. 82 synthesized instruments (keys, mallets, plucked and bowed strings, winds, brass, synths, basses) voiced so that nothing is piercing, drums and world percussion, sound effects, a physically-modelled car engine (`car_engine`), a small formant speech synthesizer (letters, numbers, short words; English + Spanish; human, robot, android, synth, bad/evil robot, monster, giant, alien and ghost voices) and an effects rack, all rendered offline to WAV from a JSON spec or a one-line command. Built to be driven by AI agents (see `AGENTS.md`).

```
python install.py --tool          # installs the `genny` command (needs uv) and the Claude Code skill
uv tool install --editable .      # or: just the command
genny sfx coin -o coin.wav
genny seq violin "D5:.5 E5:.5 F#5:1 A5:2" --bpm 100 -o tune.wav      # with --bpm, durations are beats
genny seq bell "C5:0.1 E5:0.1 G5:0.1 C6:0.5" --fx reverb:mix=0.3 -o stinger.wav
genny say "level up!" -p voice=female -o level_up.wav
genny say "surrender" -p voice=evil_robot -o boss.wav
genny sfx car_engine -p rpm=3000 -p load=0.6 -o engine.wav
genny render examples/library/win.json
genny render examples/library/styles.json        # 35 music styles, 4-8 bars each
genny info sounds/styles/funk.wav                # loudness, sharpness, energy above 5 kHz
genny list
```

- `AGENTS.md` — the full spec format, notation and recipes (written for AI agents, works for humans too).
- `examples/library/*.json` — demo batch files (25 sounds each, and `styles.json`: one loop per music style); renders go to `sounds/` (not committed).
- `examples/build_library.py`, `examples/build_styles.py` — regenerate those batch files and render them.
- `examples/audition.py` — renders a phrase for every instrument and a hit for every drum to `sounds/audition/`.
- `examples/level_match.py` — re-measures the instruments and rewrites their level trims (run after changing a voice).
- `tests/` — plain-assert checks: `uv run python tests/test_instruments.py`, `uv run python tests/test_spec.py`.
- `skill/genny/` — a Claude Code skill (`SKILL.md`, `reference.md`, `styles.json`). `python install.py` copies it to `~/.claude/skills/genny` on Windows, macOS and Linux (`--link` to symlink it instead, `--uninstall` to remove it) and gives you `/genny ...`.

Python 3.10+, numpy, scipy. No other dependencies.

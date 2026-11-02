---
name: spatial9-remix-by-voice
description: Change a finished Spatial9 immersive mix from plain-language instructions, such as moving instruments in 3D, changing levels, adding motion, effects and acoustic spaces. Use when the user says things like "put the guitar behind me", "make the synth circle in the chorus", "add a cathedral reverb" or "turn the vocal up".
---

# Spatial9 remix by voice

Requires the Spatial9 MCP server at `https://spatial9.ai/mcp` and the `job_id` of a finished render.

## Steps

1. Read the current mix with `get_mix` (stems, positions, levels) and `get_effects`. For song structure, call `analyze_song`.
2. Translate the request into `remix_render` `changes`:
   - Position: `direction` and `height`, or exact `azimuth_deg`, `elevation_deg` and `distance`.
   - Level: `gain_db` (absolute) or `gain_change_db` (relative), or `mute`.
   - Motion: `motion.shape`, one of circle, spiral_up, rise, sink, sweep, fly_over, come_close, move_away, wander or none. Add `when` (for example `chorus`), `speed` and `clockwise`.
3. Always run `remix_render` with `preview: true` first. It is free. Describe what will change and ask the user to confirm.
4. After confirmation, run the same `changes` without `preview` and with an `idempotency_key`.

## Effects and spaces

- `find_effects` with a `query` (over 1,400 presets). Then `apply_effects` with `action: add` and a `preset_id`, or up to 6 `effects` with their `params`.
- `find_spaces` for rooms, halls and venues. Apply the best match with `apply_effects`.
- Use `target` or `stem_id` to choose which stem, or the master bus, the effect goes on.

## Rules

- Keep lead vocal, kick, snare and bass near the front centre unless the user insists otherwise.
- Every movement needs a musical moment. Avoid constant motion; it causes listener fatigue.
- Save a look the user likes with `save_mix_template` so it can be reused with `template_id`.

---
name: spatial9-immersive-mix
description: Turn a stereo song, a set of stems or a video into immersive Eclipsa Audio (IAMF) with a binaural headphone version, using the Spatial9 MCP server. Use when the user asks to make a track immersive, 3D, spatial, 360 or "Atmos-like", or to prepare music for YouTube spatial audio.
---

# Spatial9 immersive mix

Requires the Spatial9 MCP server: `https://spatial9.ai/mcp` (sign in with OAuth or send `Authorization: Bearer s9_...`), or `https://spatial9.ai/mcp/free` for the free guest allowance.

## When to use

- "Make this song immersive / spatial / 3D."
- "Turn my stems into Eclipsa Audio."
- "Give this video a spatial soundtrack for YouTube."

## Steps

1. If the user has not heard Spatial9 before, offer the free `preview_chorus` first (30-second headphone WAV, uses no project).
2. Get the source:
   - Public https link: pass it as `source_url`.
   - Local file: call `create_upload_link` with `filename`, PUT the file to `direct_upload_url`, then pass `upload_id`.
3. Start the render:
   - Mixed song or video: `create_spatial_audio` with `media_type` (`music` or `video`), `title`, optional `style` (`live_concert`, `club`, `cinema`, `intimate_studio`) and `include_binaural: true`.
   - 2 to 16 stems: `create_from_stems` with `stems: [{ url | upload_id, name, instrument }]`. Instruments: vocals, drums, bass, guitar, piano, keys, synth, strings, brass, other.
   - Always send an `idempotency_key` built from the title so a retry never starts a second render.
4. Tell the user a song usually takes 10 to 20 minutes. Poll `get_job_status` every 30 to 60 seconds, and report `stage` and `progress` in plain words.
5. When `status` is `completed`, call `get_downloads` and present each file by its `label`. Lead with the binaural headphone WAV and the YouTube-ready MP4.

## Rules

- Each render uses one project from the user's plan and is refunded automatically if it fails. Say so before the first render.
- Limits: 3 renders at once, 20 per 24 hours. Queue extra work instead of failing.
- Never invent download links. Only share URLs returned by `get_downloads`.
- If a tool returns `isError: true`, pass its message on in plain words and stop.

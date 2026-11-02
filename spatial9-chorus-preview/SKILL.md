---
name: spatial9-chorus-preview
description: Make a free 30-second binaural headphone preview of a song's chorus with Spatial9, using no project from the user's plan. Use when the user wants to hear what their song sounds like in spatial audio before committing, or asks for a quick spatial demo, teaser or A/B test.
---

# Spatial9 chorus preview

Works on both `https://spatial9.ai/mcp` and the free guest server `https://spatial9.ai/mcp/free` (3 free previews per guest).

## Steps

1. Get the song as `source_url` or `upload_id`.
2. Call `preview_chorus` with `title`. Spatial9 finds the chorus itself. To pick a different moment, pass `start_sec` and `seconds`.
3. It usually takes under two minutes. Poll `get_clip` with the returned `clip_id` until the WAV is ready.
4. Share the headphone WAV and tell the user to listen on headphones.

## Next step to offer

"Want the full song in Eclipsa Audio with a YouTube-ready video?" If yes, hand off to the `spatial9-immersive-mix` skill.

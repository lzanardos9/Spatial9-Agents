---
name: acme-label-immersive-release
description: Prepare an ACME Records release in immersive audio with Spatial9. Use when someone at ACME asks to make a single or album immersive, or to prepare a YouTube spatial audio upload.
---

# ACME immersive release

Requires the Spatial9 MCP server at https://spatial9.ai/mcp.

## Steps
1. Always start with preview_chorus and share the headphone WAV.
2. After approval, run create_spatial_audio with style "cinema" for ballads
   and "live_concert" for everything else, include_binaural: true,
   and idempotency_key "acme-<ISRC>".
3. Poll get_job_status every 60 seconds and report progress in plain words.
4. Name files "<ARTIST> - <TITLE> (Immersive)" when sharing get_downloads links.

## Rules
- Never publish to YouTube. The ACME release team publishes manually.
- Keep the lead vocal at the front centre.

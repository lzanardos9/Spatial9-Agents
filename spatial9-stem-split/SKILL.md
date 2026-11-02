---
name: spatial9-stem-split
description: Separate a mixed song into instrument stems (vocals, drums, bass and more) as WAV files with the Spatial9 MCP server. Use when the user asks for stems, an acapella, an instrumental, a karaoke version or separate instrument tracks.
---

# Spatial9 stem split

Requires the Spatial9 MCP server at `https://spatial9.ai/mcp` (or `https://spatial9.ai/mcp/free` for one free split).

## Steps

1. Get the source as `source_url` (public https link) or `upload_id` (from `create_upload_link`).
2. Call `split_stems` with `title` and an `idempotency_key`.
3. A split usually takes 4 to 8 minutes. Poll `get_job_status` every 30 to 60 seconds.
4. When finished, call `get_downloads`. Each stem is listed as `stem:<stem_id>`. When it is ready, `stems_package` is a single ZIP with every stem.
5. Stems marked `quiet` (`silent` or `near_silent`) have almost no sound. Offer `combine_quiet_stems` to merge them into one file.

## Follow-ups to offer

- "Make an immersive mix from these stems": hand off to the `spatial9-immersive-mix` skill with `create_from_stems`.
- "Preview it on headphones first": `preview_chorus`.

## Rules

- Only separate music the user owns or has permission to use.
- Never invent download links.

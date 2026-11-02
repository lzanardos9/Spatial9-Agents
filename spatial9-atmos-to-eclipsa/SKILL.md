---
name: spatial9-atmos-to-eclipsa
description: Convert Dolby Digital (AC-3), Dolby Digital Plus (E-AC-3), TrueHD or an ADM BWF Dolby Atmos master into Eclipsa Audio (IAMF) for YouTube and supported TVs, using the Spatial9 MCP server. Use when the user has an Atmos, ADM, .ec3, .ac3 or TrueHD file and wants Eclipsa Audio or YouTube spatial audio.
---

# Spatial9 Atmos to Eclipsa Audio

Requires the Spatial9 MCP server at `https://spatial9.ai/mcp` (or `https://spatial9.ai/mcp/free` for one free conversion).

## Steps

1. Get the file. ADM masters are large, so for local files use `create_upload_link` (up to 2 GB, link valid for 2 hours) and PUT the file to `direct_upload_url`.
2. Call `convert_dolby_to_eclipsa` with `source_url` or `upload_id`, a `title`, `include_binaural: true` and an `idempotency_key`.
3. Optional: `include_video: true` with `visual_url` or `visual_upload_id` for a YouTube-ready MP4.
4. Poll `get_job_status` every 30 to 60 seconds, then call `get_downloads`.

## What to tell the user

- ADM BWF masters keep their beds and objects.
- AC-3, E-AC-3 and TrueHD files keep their speaker channels (up to 7.1). The Dolby Atmos height and object layer inside those files is not kept. If the user has the ADM master, recommend using it instead.
- Each conversion uses one project from the plan and is refunded if it fails.

---
name: spatial9-release-publisher
description: Publish a finished Spatial9 immersive render to the user's YouTube channel and make a vertical 9:16 social clip for Shorts, Reels and TikTok. Use when the user asks to upload, publish, post or promote a spatial audio render.
---

# Spatial9 release publisher

Requires the Spatial9 MCP server at `https://spatial9.ai/mcp` and a finished `job_id`. If YouTube is not connected yet, `publish_to_youtube` returns a link where the user connects their channel once; call it again after they confirm.

## Steps

1. Confirm the render is finished with `get_job_status`.
2. Ask for, or propose, `title`, `description` and `tags`. Default to `privacy: unlisted` so the user can check it before going public.
3. Call `publish_to_youtube` with `job_id`, `privacy`, `title`, `description` and `tags`.
4. Poll `get_youtube_upload` until the video link is returned, then share it.
5. Offer a vertical clip: `create_social_clip` with the `job_id`, then poll `get_clip` with the returned `clip_id` and share the 9:16 MP4.

## Rules

- Never publish as `public` without the user's explicit confirmation in this conversation.
- Limit: 5 YouTube publishes per 24 hours.
- YouTube can take a while to process spatial audio after upload. Tell the user the immersive sound may appear a little after the video.

---
name: spatial9-enterprise-catalog
description: Run governed, repeatable Spatial9 immersive audio renders for a music catalog from enterprise data and AI platforms such as Databricks, Snowflake, Google Vertex AI and Amazon Bedrock. Use when the user asks to batch-render a catalog, schedule nightly renders, call Spatial9 from a warehouse, lakehouse, notebook, stored procedure, Lambda, Cloud Run job or enterprise agent, or keep an audit trail of renders.
---

# Spatial9 enterprise catalog

Requires the Spatial9 MCP server at `https://spatial9.ai/mcp` with a service key (`Authorization: Bearer s9_...`) created at https://spatial9.ai/connect. Store the key in the platform's secret store: Databricks secret scopes, Snowflake secrets, Google Secret Manager or AWS Secrets Manager. Never paste it into code, notebooks or prompts.

## Steps

1. Read the work list from a governed table (for example `catalog.renders_queue`) with `track_id`, `title`, `source_url` or a file path, and `status = 'pending'`.
2. For a file that is not on a public https link, call `create_upload_link` and PUT the file to `direct_upload_url` (2 hours, up to 2 GB).
3. Call `create_spatial_audio` with `upload_id` or `source_url`, `media_type: "music"`, `title`, `style`, `include_binaural: true` and `idempotency_key = "<platform>-<track_id>-<version>"`.
4. Keep at most 3 renders running at once and at most 20 per day per account. Leave the rest as `pending` for the next run.
5. Poll `get_job_status` every 30 to 60 seconds, or schedule a second short job that checks every running row.
6. When `status` is `completed`, call `get_downloads` and copy `binaural`, `iamf` and `youtube_video` into governed storage (Volumes, stages, Cloud Storage or S3).
7. Write `job_id`, `status`, `stage`, file paths and timestamps back to the table so every render is auditable.

## Platform recipes

- Databricks: `examples/enterprise/databricks/`
- Snowflake: `examples/enterprise/snowflake/`
- Google Vertex AI and Cloud Run: `examples/enterprise/vertex-ai/`
- Amazon Bedrock and AWS: `examples/enterprise/bedrock/`
- Shared Python client with the MCP handshake: `examples/enterprise/shared/spatial9_mcp.py`

## Rules

- Only render music the organisation owns or has permission to use.
- Reuse the same `idempotency_key` on retries. A retry must never start a second render.
- A failed render refunds its project. Record the plain-language reason and do not retry more than twice.
- Never invent download links. Only use URLs returned by `get_downloads`.
- Never log the key or full download URLs in shared logs.
- Microsoft Fabric is not a supported platform for these recipes.

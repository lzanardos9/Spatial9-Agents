-- Spatial9 on Databricks: one-time setup in Unity Catalog.
-- Run as a metastore or catalog admin. Replace `media` with your catalog.

-- 1. Keep the Spatial9 key in a secret scope (run once from the Databricks CLI):
--      databricks secrets create-scope spatial9
--      databricks secrets put-secret spatial9 api_key

-- 2. A governed HTTP connection. Agents and SQL can use it without ever seeing the key.
CREATE CONNECTION IF NOT EXISTS spatial9_mcp TYPE HTTP
OPTIONS (
  host 'https://spatial9.ai',
  port '443',
  base_path '/mcp',
  bearer_token secret('spatial9', 'api_key')
);

-- Only the catalog team may call it.
GRANT USE CONNECTION ON CONNECTION spatial9_mcp TO `catalog-engineers`;

-- 3. The work queue. One row per track and version.
CREATE TABLE IF NOT EXISTS media.spatial.renders_queue (
  track_id      STRING NOT NULL,
  version       INT    NOT NULL DEFAULT 1,
  title         STRING NOT NULL,
  source_path   STRING,                 -- /Volumes/media/spatial/masters/<file>.wav
  style         STRING DEFAULT 'live_concert',
  status        STRING DEFAULT 'pending',  -- pending, running, completed, failed
  job_id        STRING,
  stage         STRING,
  binaural_path STRING,
  iamf_path     STRING,
  error         STRING,
  updated_at    TIMESTAMP
) TBLPROPERTIES (delta.feature.allowColumnDefaults = 'supported');

-- 4. Where finished files land.
CREATE VOLUME IF NOT EXISTS media.spatial.masters;
CREATE VOLUME IF NOT EXISTS media.spatial.immersive;

-- 5. Optional: expose the server to Databricks agents through Unity AI Gateway "MCP Services"
--    (UI, API, SDK or Terraform). Point it at the spatial9_mcp connection, then agents call
--    https://<workspace>/ai-gateway/mcp-services/media.spatial.spatial9 with their own identity.

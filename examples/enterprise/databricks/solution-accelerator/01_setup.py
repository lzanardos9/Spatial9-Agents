# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Setup: schema, Volumes, tables and a governed connection
# MAGIC Run once. Before you start, store your keys from the Databricks CLI:
# MAGIC ```
# MAGIC databricks secrets create-scope spatial9
# MAGIC databricks secrets put-secret spatial9 api_key              # s9_... key from spatial9.ai/connect (MCP and A2A)
# MAGIC databricks secrets put-secret spatial9 spatializer_api_key  # only for the REST API route (notebook 05)
# MAGIC ```

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {NS} COMMENT 'Spatial9 Solutions Accelerator'")  # noqa: F821
for volume in ("masters", "stems", "immersive", "checkpoints"):
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {NS}.{volume}")  # noqa: F821

# COMMAND ----------

# The queue. route picks the integration:
#   mcp -> full immersive renders, tool by tool (notebook 03)
#   a2a -> hand a whole task to the Spatial9 agent: stems, Dolby or ADM conversion, chorus previews (notebook 04)
#   api -> stems in, Dolby Atmos and IAMF masters out, with the Spatializer REST API (notebook 05)
spark.sql(f"""
CREATE TABLE IF NOT EXISTS {QUEUE} (
  track_id     STRING NOT NULL,
  version      INT    NOT NULL,
  route        STRING NOT NULL,
  skill        STRING NOT NULL,
  title        STRING NOT NULL,
  source_path  STRING,
  style        STRING,
  instruments  STRING COMMENT 'REST API route only: JSON of instrument UUID to stem file names',
  status       STRING NOT NULL COMMENT 'pending, running, completed or failed',
  job_id       STRING,
  stage        STRING,
  outputs      STRING COMMENT 'JSON of file id to Volume path',
  error        STRING,
  updated_at   TIMESTAMP,
  CONSTRAINT route_ok CHECK (route IN ('mcp', 'a2a', 'api')),
  CONSTRAINT status_ok CHECK (status IN ('pending', 'running', 'completed', 'failed'))
) CLUSTER BY (status, route)
""")

spark.sql(f"""
CREATE TABLE IF NOT EXISTS {EVENTS} (
  track_id STRING, version INT, route STRING, job_id STRING, event STRING, detail STRING, at TIMESTAMP
) COMMENT 'Append-only audit trail for every Spatial9 render'
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Optional: a governed HTTP connection for Databricks agents
# MAGIC With this connection, agents and SQL users can reach Spatial9 without ever seeing the key.
# MAGIC Register it as an external MCP server in Unity AI Gateway (MCP Services) so Mosaic AI agents can call
# MAGIC Spatial9 tools. Menu names change often, so check the current Databricks documentation.

# COMMAND ----------

spark.sql(f"""
CREATE CONNECTION IF NOT EXISTS spatial9_mcp TYPE HTTP
OPTIONS (host 'https://spatial9.ai', port '443', base_path '/mcp', bearer_token secret('{SCOPE}', 'api_key'))
""")
# spark.sql("GRANT USE CONNECTION ON CONNECTION spatial9_mcp TO `catalog-engineers`")

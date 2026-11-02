# Spatial9 on Databricks

Render a music catalog stored in Unity Catalog Volumes, with the key in a secret scope and every result written back to a Delta table.

Want the complete, deployable version with MCP, A2A and REST API routes, Auto Loader, an audit trail and dashboards? Use the [Solutions Accelerator](solution-accelerator/README.md).

| File | What it does |
|---|---|
| [setup.sql](setup.sql) | Secret scope, governed HTTP connection, queue table and Volumes |
| [spatial9_catalog_job.py](spatial9_catalog_job.py) | Lakeflow Job task: finishes running renders, starts up to 3 new ones |
| [../shared/spatial9_mcp.py](../shared/spatial9_mcp.py) | MCP handshake and tool calls with `requests` |

## Run it

1. Run `setup.sql` once.
2. Copy `spatial9_mcp.py` and `spatial9_catalog_job.py` into one Workspace folder.
3. Create a Lakeflow Job with a Python task pointing at the job file. Schedule it every 15 minutes.
4. Insert rows with `status = 'pending'`. Finished files appear in `/Volumes/media/spatial/immersive`.

## Agents on Databricks

To let a Databricks agent call Spatial9 tools directly, register the `spatial9_mcp` connection as an external MCP server in Unity AI Gateway (MCP Services). Access is then governed by `USE CONNECTION` grants and audited like any other Unity Catalog object. Menu names change often, so check the current Databricks docs for the exact steps.

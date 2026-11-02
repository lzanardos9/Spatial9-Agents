# Spatial9 Solutions Accelerator for Databricks

Turn a music catalog in Unity Catalog into immersive audio on a schedule, with every render governed, idempotent and audited. One Asset Bundle, six notebooks, three ways to reach Spatial9.

```
masters Volume ──Auto Loader──> bronze_masters ──MERGE──> render_queue (Delta, source of truth)
                                                              │
                         ┌────────────────────────────────────┼─────────────────────────────┐
                    route = mcp                          route = a2a                    route = api
              03 Spatial9 MCP server               04 Spatial9 A2A agent         05 Spatializer REST API
         create_spatial_audio, get_job_status   split_stems, convert_dolby,     stems -> Dolby Atmos + IAMF
          get_downloads (Eclipsa, binaural)       preview_chorus (free)            (tus resumable upload)
                         └────────────────────────────────────┼─────────────────────────────┘
                                                              │
                                  immersive Volume  +  render_events (audit)  ──>  06 gold views
```

## Which route should a track take?

| Route | Use it when | What comes back |
|---|---|---|
| `mcp` | You have a stereo master and want the full Spatial9 render | Eclipsa Audio (IAMF), YouTube-ready MP4, binaural headphone WAV |
| `a2a` | You want to hand a whole task to the Spatial9 agent and just follow it | Stems as WAV, Dolby or ADM converted to Eclipsa Audio, or a free 30-second chorus preview |
| `api` | You already have stems and need delivery masters | Dolby Atmos master and IAMF from the Spatializer REST API |

MCP and A2A use the same `s9_` key and share the plan limits: 3 renders at once and 20 per day. Failed renders are refunded automatically. Chorus previews are free.

## Files

| File | What it does |
|---|---|
| [databricks.yml](databricks.yml) | Asset Bundle: one job, five tasks, every 15 minutes (paused until you unpause it) |
| [00_config.py](00_config.py) | Widgets, table names, limits and helpers shared by every notebook |
| [01_setup.py](01_setup.py) | Schema, four Volumes, the queue and audit tables, optional governed HTTP connection |
| [02_ingest_masters.py](02_ingest_masters.py) | Auto Loader picks up new masters and queues them once |
| [03_render_mcp.py](03_render_mcp.py) | Full immersive renders through the MCP server |
| [04_delegate_a2a.py](04_delegate_a2a.py) | Stems, Dolby or ADM conversion and chorus previews through the A2A agent |
| [05_atmos_rest_api.py](05_atmos_rest_api.py) | Stems to Dolby Atmos and IAMF masters with resumable uploads |
| [06_gold_views.sql](06_gold_views.sql) | Coverage, daily throughput and failure reasons for dashboards or Genie |
| [../../shared/spatial9_mcp.py](../../shared/spatial9_mcp.py) | MCP client with `requests` only |
| [../../shared/spatial9_a2a.py](../../shared/spatial9_a2a.py) | A2A client with `requests` only |

## Deploy in five steps

1. Create a key at https://spatial9.ai/connect and store it: `databricks secrets create-scope spatial9` then `databricks secrets put-secret spatial9 api_key`. For the REST API route, also store `spatializer_api_key`.
2. Download this repo (the zip at https://spatial9.ai/agents/skills) and open a terminal in this folder.
3. `databricks bundle deploy -t dev --var warehouse_id=<your SQL warehouse id>`
4. Run `01_setup.py` once from the workspace, then drop a few WAV files into the `masters` Volume.
5. `databricks bundle run spatial9_accelerator -t dev`. When the first renders look right, unpause the schedule.

## Sending a track to a different route

```sql
-- A free chorus preview through the A2A agent
INSERT INTO main.spatial9_accelerator.render_queue (track_id, version, route, skill, title, source_path, status, updated_at)
VALUES ('night_drive', 1, 'a2a', 'preview_chorus', 'Night Drive', '/Volumes/main/spatial9_accelerator/masters/night_drive.wav', 'pending', current_timestamp());

-- Dolby Atmos and IAMF masters from stems through the REST API
INSERT INTO main.spatial9_accelerator.render_queue (track_id, version, route, skill, title, source_path, instruments, status, updated_at)
VALUES ('night_drive', 1, 'api', 'atmos_master', 'Night Drive', '/Volumes/main/spatial9_accelerator/stems/night_drive',
        '{"<bass uuid>": ["BASS.wav"], "<drums uuid>": ["DRUMS.wav"], "<vocals uuid>": ["LEAD VOCALS.wav"]}', 'pending', current_timestamp());
```

## Governance built in

- The key lives only in a secret scope and is redacted in notebook output.
- Every start uses an idempotency key (`databricks-<track>-v<version>`), so retries never render or charge twice.
- `free_slots()` respects 3 renders at once and 20 per day before anything starts.
- `render_events` records every start, completion and failure for audit.
- Only render music you own or license.

## Agents on Databricks

Run `01_setup.py` to create the `spatial9_mcp` HTTP connection, then register it as an external MCP server in Unity AI Gateway (MCP Services). Mosaic AI agents can then call Spatial9 tools under their own identity, governed by `USE CONNECTION` grants. Databricks menus change often, so check the current Databricks documentation for the exact steps.

Microsoft Fabric is not supported.

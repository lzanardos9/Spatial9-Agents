# Spatial9 open source pipeline

A complete spatial audio pipeline built only from open source tools, with Spatial9 reached over open protocols (MCP and A2A over HTTPS). Drop a WAV into a bucket and, a few minutes later, a browser page plays the binaural version while Eclipsa Audio (IAMF) and an MP4 land in storage.

Read the full guide: https://spatial9.ai/blog/open-source-spatial-audio-pipeline-real-time-spatial9

```
 WAV into MinIO ──event──▶ Kafka (audio.uploaded) ──▶ worker.py
                                                        │  FFmpeg check + loudness
                                                        │  MCP create_upload_link + PUT
                                                        │  A2A message/send (spatial_audio)
                                                        ▼
                                            Spatial9 agent (spatial9.ai/a2a)
                                                        │ push on every state change
                                                        ▼
 browser ◀── SSE /events ◀── Valkey pub/sub ◀── webhook.py ──▶ MinIO immersive bucket
                                                        └──▶ PostgreSQL tracks + track_events
 Prometheus ◀── /metrics (worker, webhook) ──▶ Grafana
 Dagster (dagster_catalog.py): nightly backfill of old masters + daily report
```

## Files

| File | What it does |
|---|---|
| `docker-compose.yml` | MinIO, Apache Kafka, PostgreSQL, Valkey, worker, webhook, Prometheus and Grafana |
| `env.example` | Every setting; copy to `.env` |
| `schema.sql` | `tracks` and the append-only `track_events` |
| `worker.py` | Kafka consumer, FFmpeg checks, slot control, MCP upload, A2A task, fallback polling |
| `webhook.py` | FastAPI: verified A2A push notifications, MinIO copies, Server-Sent Events, metrics |
| `preview.html` | Live status page that plays the binaural result |
| `dagster_catalog.py` | Nightly backfill and report assets |
| `prometheus.yml` | Scrapes the worker and webhook |

The worker imports the shared clients in `../enterprise/shared` (`spatial9_mcp.py`, `spatial9_a2a.py`).

## Run it

1. Create a key at https://spatial9.ai/connect, then `cp env.example .env` and fill it in.
2. Make the webhook reachable over https (reverse proxy or tunnel) and put that address in `PUBLIC_WEBHOOK_URL`.
3. `docker compose up -d`
4. Create the bucket and the event rule with the MinIO client:
   ```bash
   mc alias set local http://localhost:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
   mc mb local/masters
   mc event add local/masters arn:minio:sqs::PRIMARY:kafka --event put
   ```
5. `mc cp my-song.wav local/masters/` and open http://localhost:8080, then follow `my-song`.

## Limits and safety

- 3 renders at once and 20 per day per key; `free_slots()` enforces both before anything starts. Failed renders are refunded.
- `messageId` is `oss-spatial_audio-<track>-v<version>`, so a retry never starts a second render.
- Pushes are accepted only with the right `X-A2A-Notification-Token` (constant-time check), and the task is re-read with `tasks/get`.
- Keys live only in `.env`; never commit it.

Licences change (MinIO, Grafana and Redis have all changed terms in recent years). Check each project before production use. MIT licence for these examples.

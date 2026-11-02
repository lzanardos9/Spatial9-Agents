"""Dagster definitions for the batch side: backfilling an existing catalog and a daily report.

The worker handles new uploads in real time. These assets cover the jobs a catalog team runs on a schedule:
  catalog_backfill  queue every master already in MinIO that has never been registered
  daily_report      a small table of yesterday's results for Grafana or an email

Run locally:  pip install dagster dagster-webserver  then  dagster dev -f dagster_catalog.py
"""
from __future__ import annotations

import os
import pathlib
import re

import psycopg
from dagster import AssetExecutionContext, Definitions, MaterializeResult, ScheduleDefinition, asset, define_asset_job
from minio import Minio

AUDIO = {".wav", ".flac", ".aif", ".aiff"}
TRACK_ID = re.compile(r"[^a-z0-9-]+")


def _db() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)


@asset(description="Registers masters that were in MinIO before the pipeline existed. Safe to re-run.")
def catalog_backfill(context: AssetExecutionContext) -> MaterializeResult:
    store = Minio(os.environ["MINIO_ENDPOINT"], os.environ["MINIO_ROOT_USER"], os.environ["MINIO_ROOT_PASSWORD"], secure=False)
    added = 0
    with _db() as conn:
        for obj in store.list_objects("masters", recursive=True):
            if pathlib.Path(obj.object_name).suffix.lower() not in AUDIO:
                continue
            track_id = TRACK_ID.sub("-", pathlib.Path(obj.object_name).stem.lower()).strip("-")[:80]
            row = conn.execute(
                "INSERT INTO tracks (track_id, object_key) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING 1",
                (track_id, obj.object_name),
            ).fetchone()
            if row:
                conn.execute("INSERT INTO track_events (track_id, version, event, detail) VALUES (%s, 1, 'registered', 'backfill')",
                             (track_id,))
                added += 1
    context.log.info("Queued %s masters; the worker starts them as render slots free up.", added)
    return MaterializeResult(metadata={"queued": added})


@asset(deps=[catalog_backfill], description="Yesterday's results by status, for dashboards.")
def daily_report() -> MaterializeResult:
    with _db() as conn:
        rows = conn.execute(
            "SELECT event, count(*) FROM track_events WHERE at >= current_date - 1 AND at < current_date GROUP BY event"
        ).fetchall()
    return MaterializeResult(metadata={event: count for event, count in rows})


nightly = define_asset_job("nightly_catalog", selection=[catalog_backfill, daily_report])

defs = Definitions(
    assets=[catalog_backfill, daily_report],
    jobs=[nightly],
    schedules=[ScheduleDefinition(job=nightly, cron_schedule="0 2 * * *")],
)

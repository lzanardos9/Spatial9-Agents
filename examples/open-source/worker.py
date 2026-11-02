"""Spatial9 open source pipeline worker.

Flow for every new master that lands in the MinIO `masters` bucket:
  1. Kafka delivers the MinIO event (topic audio.uploaded). We register the track once in PostgreSQL.
  2. FFmpeg checks the file: real audio, long enough, and measures integrated loudness.
  3. When a render slot is free (3 at once, 20 per day), we upload it to Spatial9 with MCP
     and hand the task to the Spatial9 A2A agent, asking for push notifications to webhook.py.
  4. Every two minutes we also ask A2A directly about tasks that went quiet, so a missed
     webhook never leaves a track stuck.

Run with docker compose (see README.md). Secrets come from the environment, never from code.
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import re
import subprocess
import tempfile
import time
import urllib.parse

import psycopg
import requests
from confluent_kafka import Consumer
from minio import Minio
from prometheus_client import Counter, Gauge, start_http_server

from spatial9_a2a import Spatial9A2A, Spatial9A2AError   # from examples/enterprise/shared
from spatial9_mcp import Spatial9MCP, Spatial9Error

log = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MAX_RUNNING, DAILY_LIMIT = 3, 20
MIN_SECONDS = 30
AUDIO = {".wav", ".flac", ".aif", ".aiff"}
TRACK_ID = re.compile(r"[^a-z0-9-]+")

STARTED = Counter("spatial9_tasks_started_total", "Spatial9 tasks started")
REJECTED = Counter("spatial9_tracks_rejected_total", "Masters rejected by the FFmpeg check")
RUNNING = Gauge("spatial9_tasks_running", "Spatial9 tasks currently submitted or working")

db = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
store = Minio(os.environ["MINIO_ENDPOINT"], os.environ["MINIO_ROOT_USER"], os.environ["MINIO_ROOT_PASSWORD"], secure=False)
mcp = Spatial9MCP(api_key=os.environ["SPATIAL9_API_KEY"])
a2a = Spatial9A2A(api_key=os.environ["SPATIAL9_API_KEY"])


def event(track_id: str, version: int, name: str, detail: str = "") -> None:
    db.execute("INSERT INTO track_events (track_id, version, event, detail) VALUES (%s, %s, %s, %s)",
               (track_id, version, name, detail))


def register(message: bytes) -> None:
    """Turn one MinIO bucket event into a pending track. Duplicates are ignored."""
    body = json.loads(message)
    for record in body.get("Records", []):
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])     # MinIO URL-encodes keys
        if pathlib.Path(key).suffix.lower() not in AUDIO:
            continue
        track_id = TRACK_ID.sub("-", pathlib.Path(key).stem.lower()).strip("-")[:80]
        inserted = db.execute(
            "INSERT INTO tracks (track_id, object_key) VALUES (%s, %s) ON CONFLICT DO NOTHING RETURNING 1",
            (track_id, key),
        ).fetchone()
        if inserted:
            event(track_id, 1, "registered", key)


def check_audio(path: str) -> tuple[bool, float | None, str]:
    """Return (ok, integrated LUFS, reason). Uses only ffprobe and ffmpeg."""
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, text=True, timeout=120,
    )
    if probe.returncode != 0:
        return False, None, "Not a readable audio file."
    duration = float(json.loads(probe.stdout).get("format", {}).get("duration", 0))
    if duration < MIN_SECONDS:
        return False, None, f"Too short ({duration:.0f} s). Spatial9 needs at least {MIN_SECONDS} s."
    # loudnorm in analysis mode prints a JSON block with the measured integrated loudness on stderr.
    meter = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, timeout=600,
    )
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", meter.stderr)
    lufs = float(json.loads(match.group(0))["input_i"]) if match else None
    return True, lufs, ""


def free_slots() -> int:
    running = db.execute("SELECT count(*) FROM tracks WHERE status IN ('submitted', 'working')").fetchone()[0]
    today = db.execute(
        "SELECT count(*) FROM track_events WHERE event = 'started' AND at > now() - interval '24 hours'"
    ).fetchone()[0]
    RUNNING.set(running)
    return max(0, min(MAX_RUNNING - running, DAILY_LIMIT - today))


def start_pending() -> None:
    slots = free_slots()
    if not slots:
        return
    rows = db.execute(
        "SELECT track_id, version, object_key FROM tracks WHERE status = 'pending' ORDER BY updated_at LIMIT %s",
        (slots,),
    ).fetchall()
    for track_id, version, key in rows:
        with tempfile.TemporaryDirectory() as tmp:
            local = os.path.join(tmp, pathlib.Path(key).name)
            store.fget_object("masters", key, local)
            ok, lufs, reason = check_audio(local)
            if not ok:
                db.execute("UPDATE tracks SET status='rejected', error=%s, updated_at=now() WHERE track_id=%s AND version=%s",
                           (reason, track_id, version))
                event(track_id, version, "rejected", reason)
                REJECTED.inc()
                continue
            try:
                link = mcp.call("create_upload_link", {"filename": pathlib.Path(local).name, "media_type": "music"})
                with open(local, "rb") as f:
                    requests.put(link["direct_upload_url"], data=f, timeout=3600).raise_for_status()
                task = a2a.send(
                    message_id=f"oss-spatial_audio-{track_id}-v{version}",   # same id on retry = same task
                    skill="spatial_audio",
                    data={"upload_id": link["upload_id"], "title": track_id.replace("-", " ").title(),
                          "style": "live_concert", "include_binaural": True},
                )
                a2a.set_webhook(task["id"], os.environ["PUBLIC_WEBHOOK_URL"], os.environ["A2A_WEBHOOK_TOKEN"])
            except (Spatial9Error, Spatial9A2AError, requests.RequestException) as e:
                db.execute("UPDATE tracks SET error=%s, updated_at=now() WHERE track_id=%s AND version=%s",
                           (str(e)[:500], track_id, version))
                log.warning("Could not start %s: %s", track_id, e)
                continue
        db.execute(
            "UPDATE tracks SET status=%s, task_id=%s, loudness_lufs=%s, error='', updated_at=now() "
            "WHERE track_id=%s AND version=%s",
            (a2a.state(task), task["id"], lufs, track_id, version),
        )
        event(track_id, version, "started", task["id"])
        STARTED.inc()


def poll_quiet_tasks() -> None:
    """Safety net for missed webhooks: ask A2A about tasks with no update for 5 minutes."""
    rows = db.execute(
        "SELECT task_id FROM tracks WHERE status IN ('submitted', 'working') AND updated_at < now() - interval '5 minutes'"
    ).fetchall()
    for (task_id,) in rows:
        try:
            task = a2a.get(task_id)
        except Spatial9A2AError as e:
            log.warning("tasks/get failed for %s: %s", task_id, e)
            continue
        # Re-send the task to our own webhook so one code path handles every state change.
        requests.post(
            "http://webhook:8080/a2a/webhook", json=task, timeout=30,
            headers={"X-A2A-Notification-Token": os.environ["A2A_WEBHOOK_TOKEN"]},
        )


def main() -> None:
    start_http_server(9100)                                   # Prometheus scrapes this port
    consumer = Consumer({"bootstrap.servers": os.environ["KAFKA_BROKERS"], "group.id": "spatial9-worker",
                         "auto.offset.reset": "earliest", "enable.auto.commit": False})
    consumer.subscribe(["audio.uploaded"])
    last_poll = 0.0
    while True:
        msg = consumer.poll(5.0)
        if msg is not None and not msg.error():
            register(msg.value())
            consumer.commit(msg)                              # commit only after the row exists
        start_pending()
        if time.time() - last_poll > 120:
            poll_quiet_tasks()
            last_poll = time.time()


if __name__ == "__main__":
    main()

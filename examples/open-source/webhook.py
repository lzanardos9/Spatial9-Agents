"""Real-time side of the open source pipeline (FastAPI).

  POST /a2a/webhook        Spatial9 A2A push notifications land here (and the worker's fallback polls).
  GET  /events/{track_id}  Server-Sent Events: the browser gets every state change the moment it happens.
  GET  /                   preview.html, a tiny page that listens to /events and plays the binaural result.
  GET  /metrics            Prometheus metrics.

Security: the push is only trusted after the X-A2A-Notification-Token matches, and even then we
re-read the task from Spatial9 with tasks/get instead of trusting the posted body.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import os
import pathlib
import re

import psycopg
import redis
import redis.asyncio as aredis
import requests
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from minio import Minio
from prometheus_client import Counter, make_asgi_app

from spatial9_a2a import FINAL, Spatial9A2A, Spatial9A2AError

app = FastAPI(title="Spatial9 open source pipeline")
app.mount("/metrics", make_asgi_app())

TOKEN = os.environ["A2A_WEBHOOK_TOKEN"]
TRACK_ID = re.compile(r"^[a-z0-9-]{1,80}$")
PUSHES = Counter("spatial9_webhook_pushes_total", "A2A push notifications accepted")

a2a = Spatial9A2A(api_key=os.environ["SPATIAL9_API_KEY"])
bus = redis.Redis.from_url(os.environ["VALKEY_URL"])
store = Minio(os.environ["MINIO_ENDPOINT"], os.environ["MINIO_ROOT_USER"], os.environ["MINIO_ROOT_PASSWORD"], secure=False)


def db() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)


def publish(track_id: str, payload: dict) -> None:
    bus.publish(f"track:{track_id}", json.dumps(payload))


def apply_task(task_id: str) -> None:
    """Read the task from Spatial9, update PostgreSQL, copy finished files, tell the browsers."""
    try:
        task = a2a.get(task_id)
    except Spatial9A2AError:
        return                                                # worker's fallback poll will retry
    state = a2a.state(task)
    with db() as conn:
        row = conn.execute("SELECT track_id, version FROM tracks WHERE task_id = %s", (task_id,)).fetchone()
        if row is None:
            return                                            # not one of ours
        track_id, version = row
        files = [f for f in a2a.files(task) if f["url"].startswith("https://")] if state == "completed" else []
        saved = []
        if not store.bucket_exists("immersive"):
            store.make_bucket("immersive")
        for f in files:
            key = f"{track_id}/v{version}/{pathlib.Path(f['name']).name}"
            with requests.get(f["url"], stream=True, timeout=600) as r:
                r.raise_for_status()
                store.put_object("immersive", key, r.raw, length=-1, part_size=16 * 1024 * 1024)
            saved.append({"name": f["name"], "key": key})
        error = task.get("status", {}).get("message", {}) if state == "failed" else {}
        reason = next((p.get("text", "") for p in error.get("parts", []) if p.get("kind") == "text"), "")
        conn.execute(
            "UPDATE tracks SET status=%s, outputs=CASE WHEN %s THEN %s::jsonb ELSE outputs END, error=%s, updated_at=now() "
            "WHERE track_id=%s AND version=%s",
            (state, bool(saved), json.dumps(saved), reason, track_id, version),
        )
        conn.execute("INSERT INTO track_events (track_id, version, event, detail) VALUES (%s, %s, %s, %s)",
                     (track_id, version, state, reason or task_id))
    # Browsers get the temporary Spatial9 links for instant playback while copies sit in MinIO.
    publish(track_id, {"state": state, "final": state in FINAL, "error": reason,
                       "files": [{"name": f["name"], "url": f["url"]} for f in files]})


@app.post("/a2a/webhook", status_code=202)
async def a2a_webhook(request: Request, background: BackgroundTasks) -> dict:
    sent = request.headers.get("X-A2A-Notification-Token", "")
    if not hmac.compare_digest(sent, TOKEN):                  # constant-time comparison
        raise HTTPException(status_code=401, detail="Unauthorized")
    body = await request.json()
    task_id = body.get("id") if isinstance(body, dict) else None
    if not isinstance(task_id, str) or not task_id:
        raise HTTPException(status_code=400, detail="Missing task id")
    PUSHES.inc()
    background.add_task(apply_task, task_id)                  # answer fast, do the work afterwards
    return {"accepted": True}


@app.get("/events/{track_id}")
async def events(track_id: str, request: Request) -> StreamingResponse:
    if not TRACK_ID.match(track_id):
        raise HTTPException(status_code=404, detail="Unknown track")

    def current() -> dict | None:
        with db() as conn:
            row = conn.execute("SELECT status, error FROM tracks WHERE track_id=%s ORDER BY version DESC LIMIT 1",
                               (track_id,)).fetchone()
        return {"state": row[0], "error": row[1], "files": []} if row else None

    async def stream():
        first = await asyncio.to_thread(current)
        if first is None:
            yield "event: missing\ndata: {}\n\n"
            return
        yield f"data: {json.dumps(first)}\n\n"
        sub = aredis.Redis.from_url(os.environ["VALKEY_URL"]).pubsub()
        await sub.subscribe(f"track:{track_id}")
        try:
            while not await request.is_disconnected():
                msg = await sub.get_message(ignore_subscribe_messages=True, timeout=15)
                if msg is None:
                    yield ": keep-alive\n\n"                 # stops proxies closing an idle stream
                    continue
                yield f"data: {msg['data'].decode()}\n\n"
        finally:
            await sub.aclose()

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/")
def preview_page() -> FileResponse:
    return FileResponse(pathlib.Path(__file__).with_name("preview.html"))

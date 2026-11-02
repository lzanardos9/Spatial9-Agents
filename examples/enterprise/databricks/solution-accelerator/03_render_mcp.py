# Databricks notebook source
# MAGIC %md
# MAGIC # 03 Render with the Spatial9 MCP server
# MAGIC Finishes running renders, then starts new ones while slots are free. Safe to run every 15 minutes:
# MAGIC every call carries an idempotency key, so a retry never starts or charges a second render.

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

import json
import pathlib

import requests
from spatial9_mcp import Spatial9MCP, Spatial9Error

s9 = Spatial9MCP(api_key=secret("api_key"))


def upload(path: str) -> str:
    """Volume file -> upload_id. Links last 2 hours and accept up to 2 GB."""
    link = s9.call("create_upload_link", {"filename": pathlib.Path(path).name, "media_type": "music"})
    with open(path, "rb") as f:
        requests.put(link["direct_upload_url"], data=f, headers={"Content-Type": "audio/wav"}, timeout=3600).raise_for_status()
    return link["upload_id"]

# COMMAND ----------

# 1. Follow renders that are already running.
for row in spark.table(QUEUE).where("route = 'mcp' AND status = 'running'").collect():  # noqa: F821
    job = s9.call("get_job_status", {"job_id": row.job_id})
    if job["status"] == "completed":
        outputs = {}
        for f in s9.downloads(row.job_id, keep=("binaural", "iamf", "youtube_video")):
            outputs[f["id"]] = save(f["url"], f"{IMMERSIVE}/{row.track_id}-v{row.version}-{f['filename']}")
        update(row.track_id, row.version, "mcp", status="completed", stage="done", outputs=json.dumps(outputs))
        log(row, "completed", outputs)
    elif job["status"] in ("failed", "cancelled"):
        update(row.track_id, row.version, "mcp", status="failed", error=job.get("error", job["status"]))
        log(row, "failed", job.get("error", job["status"]))      # failed renders are refunded automatically
    elif job.get("stage") != row.stage:
        update(row.track_id, row.version, "mcp", stage=job.get("stage"))

# COMMAND ----------

# 2. Start new renders while slots are free.
for row in spark.table(QUEUE).where("route = 'mcp' AND status = 'pending'").orderBy("updated_at").limit(free_slots()).collect():  # noqa: F821
    try:
        job = s9.call("create_spatial_audio", {
            "upload_id": upload(row.source_path),
            "media_type": "music",
            "title": row.title,
            "style": row.style or "live_concert",            # live_concert, club, cinema or intimate_studio
            "include_binaural": True,                        # always ship a headphone version
            "idempotency_key": f"databricks-{row.track_id}-v{row.version}",
        })
        update(row.track_id, row.version, "mcp", status="running", job_id=job["job_id"], stage="queued", error="")
        log(row, "started", {"job_id": job["job_id"]}, job_id=job["job_id"])
    except Spatial9Error as e:                               # daily limit, unreadable file, rights problem...
        update(row.track_id, row.version, "mcp", error=str(e))
        if "limit" in str(e).lower():
            break                                            # try again on the next scheduled run

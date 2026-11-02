# Databricks notebook or Lakeflow Job task: render pending catalog rows with Spatial9.
# Schedule it every 15 minutes. Each run starts up to 3 renders and finishes the ones already running.
# Upload shared/spatial9_mcp.py next to this file (or into a Workspace folder on sys.path).
import pathlib
import requests
from datetime import datetime, timezone
from spatial9_mcp import Spatial9MCP, Spatial9Error

QUEUE = "media.spatial.renders_queue"
OUT = pathlib.Path("/Volumes/media/spatial/immersive")
MAX_RUNNING = 3                                                     # Spatial9 renders at once

s9 = Spatial9MCP(api_key=dbutils.secrets.get("spatial9", "api_key"))  # noqa: F821 - provided by Databricks


def update(track_id: str, version: int, **cols) -> None:
    """Write status back to the Delta table so every render is auditable."""
    cols["updated_at"] = datetime.now(timezone.utc)
    sets = ", ".join(f"{k} = :{k}" for k in cols)
    spark.sql(  # noqa: F821
        f"UPDATE {QUEUE} SET {sets} WHERE track_id = :track_id AND version = :version",
        args={**cols, "track_id": track_id, "version": version},
    )


def upload(path: str) -> str:
    """Volume file -> upload_id. Links last 2 hours and accept up to 2 GB."""
    link = s9.call("create_upload_link", {"filename": pathlib.Path(path).name, "media_type": "music"})
    with open(path, "rb") as f:
        requests.put(link["direct_upload_url"], data=f,
                     headers={"Content-Type": "audio/wav"}, timeout=3600).raise_for_status()
    return link["upload_id"]


# 1. Finish rows that are already running.
running = spark.table(QUEUE).where("status = 'running'").collect()  # noqa: F821
for row in running:
    job = s9.call("get_job_status", {"job_id": row.job_id})
    if job["status"] == "completed":
        paths = {}
        for f in s9.downloads(row.job_id, keep=("binaural", "iamf")):
            target = OUT / f"{row.track_id}-v{row.version}-{f['filename']}"
            with requests.get(f["url"], stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(target, "wb") as out:
                    for chunk in r.iter_content(1 << 20):
                        out.write(chunk)
            paths[f"{f['id']}_path"] = str(target)
        update(row.track_id, row.version, status="completed", stage="done", **paths)
    elif job["status"] in ("failed", "cancelled"):
        update(row.track_id, row.version, status="failed", error=job.get("error", job["status"]))
    else:
        update(row.track_id, row.version, stage=job.get("stage"))

# 2. Start new renders up to the limit.
free = MAX_RUNNING - spark.table(QUEUE).where("status = 'running'").count()  # noqa: F821
for row in spark.table(QUEUE).where("status = 'pending'").limit(max(free, 0)).collect():  # noqa: F821
    try:
        job = s9.call("create_spatial_audio", {
            "upload_id": upload(row.source_path),
            "media_type": "music",
            "title": row.title,
            "style": row.style or "live_concert",
            "include_binaural": True,
            "idempotency_key": f"databricks-{row.track_id}-v{row.version}",  # retries reuse the same job
        })
        update(row.track_id, row.version, status="running", job_id=job["job_id"], stage="queued")
    except Spatial9Error as e:            # daily limit, missing file, rights problem...
        update(row.track_id, row.version, error=str(e))
        if "limit" in str(e).lower():
            break                         # try again on the next scheduled run

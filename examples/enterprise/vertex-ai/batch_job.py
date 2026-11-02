# Cloud Run job: render tracks listed in BigQuery, save files to Cloud Storage, write results back.
# pip install requests google-cloud-bigquery google-cloud-storage
import os
from concurrent.futures import ThreadPoolExecutor

import requests
from google.cloud import bigquery, storage

from spatial9_mcp import Spatial9MCP, Spatial9Error

TABLE = "your-project.media.renders_queue"
bucket = storage.Client().bucket(os.environ["BUCKET"])
bq = bigquery.Client()


def render(row) -> dict:
    s9 = Spatial9MCP(api_key=os.environ["SPATIAL9_KEY"])   # one session per worker
    try:
        job = s9.call("create_spatial_audio", {
            "source_url": row.source_url,                    # signed URL to the master in Cloud Storage
            "media_type": "music",
            "title": row.title,
            "style": row.style or "live_concert",
            "include_binaural": True,
            "idempotency_key": f"gcp-{row.track_id}-v{row.version}",
        })
        job = s9.wait(job["job_id"])
        if job["status"] != "completed":
            return {"track_id": row.track_id, "status": job["status"], "error": job.get("error")}
        for f in s9.downloads(job["job_id"]):
            blob = bucket.blob(f"immersive/{row.track_id}/v{row.version}/{f['filename']}")
            with requests.get(f["url"], stream=True, timeout=600) as r:
                r.raise_for_status()
                blob.upload_from_file(r.raw)
        return {"track_id": row.track_id, "status": "completed", "job_id": job["job_id"]}
    except Spatial9Error as e:
        return {"track_id": row.track_id, "status": "failed", "error": str(e)}


rows = list(bq.query(f"SELECT * FROM `{TABLE}` WHERE status = 'pending' LIMIT 20").result())  # 20 per day
with ThreadPoolExecutor(max_workers=3) as pool:                                                 # 3 at once
    results = list(pool.map(render, rows))

bq.insert_rows_json(f"{TABLE}_results", results)
print(results)

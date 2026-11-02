# Databricks notebook source
# MAGIC %md
# MAGIC # 05 Stems to Dolby Atmos and IAMF with the Spatializer REST API
# MAGIC For labels that already have stems. Each row with `route = 'api'` points `source_path` at a folder in the
# MAGIC stems Volume and sets `instruments` to a JSON map of instrument UUID to stem file names, for example
# MAGIC `{"1e9d541b-...": ["BASS.wav"], "0409683b-...": ["DRUMS.wav"]}`. Run cell 2 to look up the UUIDs.
# MAGIC Full reference: https://spatial9.ai/api

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

import base64
import json
import os

import requests

BASE = "https://api.spatializer.spatial9.ai/api/v0.0.1"
HEADERS = {"Authorization": secret("spatializer_api_key")}   # the REST API takes the key as-is
CHUNK = 32 * 1024 * 1024                                      # 32 MB per PATCH


def api(method: str, path: str, **kw) -> requests.Response:
    r = requests.request(method, f"{BASE}{path}", headers={**HEADERS, **kw.pop("headers", {})}, timeout=kw.pop("timeout", 120), **kw)
    r.raise_for_status()
    return r

# COMMAND ----------

# Instrument and preset IDs for the instruments map. Run this cell when you build a new mapping.
display(spark.createDataFrame([(json.dumps(i),) for i in api("GET", "/instruments").json()], "instrument string"))  # noqa: F821

# COMMAND ----------


def tus_upload(music_id: str, kind: str, path: str) -> None:
    """Resumable upload (tus): POST to start, HEAD to find the offset, PATCH chunks until done."""
    size = os.path.getsize(path)
    name = base64.b64encode(os.path.basename(path).encode()).decode()
    start = api("POST", f"/musics/{music_id}/{kind}", headers={
        "Tus-Resumable": "1.0.0", "Upload-Length": str(size), "Upload-Metadata": f"filename {name}",
    })
    location = start.headers["Location"]
    location = location if location.startswith("http") else f"{BASE}{location}"
    offset = int(requests.head(location, headers={**HEADERS, "Tus-Resumable": "1.0.0"}, timeout=60).headers.get("Upload-Offset", 0))
    with open(path, "rb") as f:
        f.seek(offset)
        while offset < size:
            chunk = f.read(CHUNK)
            r = requests.patch(location, data=chunk, timeout=900, headers={
                **HEADERS, "Tus-Resumable": "1.0.0", "Upload-Offset": str(offset),
                "Content-Type": "application/offset+octet-stream",
            })
            r.raise_for_status()
            offset = int(r.headers.get("Upload-Offset", offset + len(chunk)))


def try_download(music_id: str, fmt: str, target: str) -> bool:
    """The master is ready when the download answers 200. Anything else means keep waiting."""
    r = requests.get(f"{BASE}/musics/{music_id}/download", params={"format": fmt}, headers=HEADERS, stream=True, timeout=900)
    if r.status_code != 200:
        return False
    with open(target, "wb") as out:
        for part in r.iter_content(1 << 20):
            out.write(part)
    return True

# COMMAND ----------

# 1. Collect finished masters.
for row in spark.table(QUEUE).where("route = 'api' AND status = 'running'").collect():  # noqa: F821
    status = api("GET", f"/musics/{row.job_id}/status").json()
    outputs = {}
    for fmt, ext in (("atmos", "wav"), ("iamf", "iamf")):
        target = f"{IMMERSIVE}/{row.track_id}-v{row.version}-{fmt}.{ext}"
        if try_download(row.job_id, fmt, target):
            outputs[fmt] = target
    if len(outputs) == 2:
        update(row.track_id, row.version, "api", status="completed", stage="done", outputs=json.dumps(outputs))
        log(row, "completed", outputs)
    else:
        update(row.track_id, row.version, "api", stage=json.dumps(status)[:500])

# COMMAND ----------

# 2. Create new musics and upload their stems.
for row in spark.table(QUEUE).where("route = 'api' AND status = 'pending'").collect():  # noqa: F821
    try:
        instruments = json.loads(row.instruments or "{}")
        files = sorted({name for names in instruments.values() for name in names})
        stereo = next((n for n in os.listdir(row.source_path) if n.lower().startswith("stereo")), None)
        body = {"name": row.title, "instruments": instruments, **({"stereo": stereo} if stereo else {})}
        music = api("POST", "/musics", params={"formats": "atmos,iamf"}, json=body).json()
        for name in files:
            tus_upload(music["id"], "stems", f"{row.source_path}/{name}")
        if stereo:
            tus_upload(music["id"], "stereo", f"{row.source_path}/{stereo}")
        update(row.track_id, row.version, "api", status="running", job_id=music["id"], stage="uploaded", error="")
        log(row, "started", {"music_id": music["id"], "stems": len(files)}, job_id=music["id"])
    except (requests.HTTPError, KeyError, ValueError, FileNotFoundError) as e:
        update(row.track_id, row.version, "api", error=str(e)[:500])

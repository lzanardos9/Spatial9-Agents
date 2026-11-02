# Databricks notebook source
# MAGIC %md
# MAGIC # 04 Delegate tasks to the Spatial9 A2A agent
# MAGIC Agent2Agent hands a whole task to Spatial9: split stems, convert a Dolby or ADM master, or make a free
# MAGIC chorus preview. Rows with `route = 'a2a'` are sent here. The messageId is the idempotency key.

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

import json
import pathlib

import requests
from spatial9_a2a import Spatial9A2A, Spatial9A2AError, FINAL
from spatial9_mcp import Spatial9MCP

a2a = Spatial9A2A(api_key=secret("api_key"))
mcp = Spatial9MCP(api_key=secret("api_key"))      # same key: used only for private upload links


def upload(path: str) -> str:
    link = mcp.call("create_upload_link", {"filename": pathlib.Path(path).name, "media_type": "music"})
    with open(path, "rb") as f:
        requests.put(link["direct_upload_url"], data=f, timeout=3600).raise_for_status()
    return link["upload_id"]

# COMMAND ----------

# 1. Follow tasks that are already running.
for row in spark.table(QUEUE).where("route = 'a2a' AND status = 'running'").collect():  # noqa: F821
    task = a2a.get(row.job_id)
    state = a2a.state(task)
    if state == "completed":
        outputs = {f["name"]: save(f["url"], f"{IMMERSIVE}/{row.track_id}-v{row.version}-{f['name']}") for f in a2a.files(task)}
        update(row.track_id, row.version, "a2a", status="completed", stage="done", outputs=json.dumps(outputs))
        log(row, "completed", outputs)
    elif state in FINAL:
        reason = (task.get("status", {}).get("message") or {}).get("parts", [{}])[0].get("text", state)
        update(row.track_id, row.version, "a2a", status="failed", error=reason)
        log(row, "failed", reason)
    elif state == "input-required":
        update(row.track_id, row.version, "a2a", status="failed", error="Spatial9 needs a file. Check source_path.")
    elif state != row.stage:
        update(row.track_id, row.version, "a2a", stage=state)

# COMMAND ----------

# 2. Send new tasks. Chorus previews are free and do not count toward the render limit.
pending = spark.table(QUEUE).where("route = 'a2a' AND status = 'pending'").orderBy("updated_at").collect()  # noqa: F821
slots = free_slots()
for row in pending:
    counts = row.skill != "preview_chorus"
    if counts and slots <= 0:
        continue
    try:
        task = a2a.send(
            message_id=f"databricks-{row.skill}-{row.track_id}-v{row.version}",
            skill=row.skill,                                  # split_stems, convert_dolby or preview_chorus
            data={"upload_id": upload(row.source_path), "title": row.title},
        )
        update(row.track_id, row.version, "a2a", status="running", job_id=task["id"], stage=a2a.state(task), error="")
        log(row, "started" if counts else "preview", {"task_id": task["id"]}, job_id=task["id"])
        slots -= int(counts)
    except Spatial9A2AError as e:
        update(row.track_id, row.version, "a2a", error=str(e))
        if "limit" in str(e).lower():
            break

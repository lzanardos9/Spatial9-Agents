# Databricks notebook source
# MAGIC %md
# MAGIC # Spatial9 Solutions Accelerator: shared settings
# MAGIC Every other notebook starts with `%run ./00_config`. Change the widgets, not the code.

# COMMAND ----------

import json
import os
import re
import sys
from datetime import datetime, timezone

dbutils.widgets.text("catalog", "main")                    # noqa: F821 - provided by Databricks
dbutils.widgets.text("schema", "spatial9_accelerator")     # noqa: F821
dbutils.widgets.text("secret_scope", "spatial9")           # noqa: F821

CATALOG = dbutils.widgets.get("catalog")                   # noqa: F821
SCHEMA = dbutils.widgets.get("schema")                     # noqa: F821
SCOPE = dbutils.widgets.get("secret_scope")                # noqa: F821

# Catalog and schema names go into SQL as identifiers, so only allow plain names.
for name in (CATALOG, SCHEMA):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", name):
        raise ValueError(f"Not a valid Unity Catalog name: {name!r}")

NS = f"{CATALOG}.{SCHEMA}"
QUEUE = f"{NS}.render_queue"          # one row per track version and route: the source of truth
EVENTS = f"{NS}.render_events"        # append-only audit trail
MASTERS = f"/Volumes/{CATALOG}/{SCHEMA}/masters"         # drop WAV, FLAC or AIFF masters here
STEMS = f"/Volumes/{CATALOG}/{SCHEMA}/stems"             # one folder per track for the REST API route
IMMERSIVE = f"/Volumes/{CATALOG}/{SCHEMA}/immersive"     # finished files land here
CHECKPOINTS = f"/Volumes/{CATALOG}/{SCHEMA}/checkpoints"

MAX_RUNNING = 3        # Spatial9 renders at once, shared by MCP and A2A
DAILY_LIMIT = 20       # renders per 24 hours

# The shared Python clients live two folders up in the Agent Skills repo (examples/enterprise/shared).
sys.path.append(os.path.abspath("../../shared"))


def secret(key: str) -> str:
    """Read from the secret scope. Databricks redacts the value in notebook output."""
    return dbutils.secrets.get(SCOPE, key)  # noqa: F821


def now():
    return datetime.now(timezone.utc)


def update(track_id: str, version: int, route: str, **cols) -> None:
    """Parameterised UPDATE, so titles or errors with quotes never break the statement."""
    cols["updated_at"] = now()
    sets = ", ".join(f"{k} = :{k}" for k in cols)
    spark.sql(  # noqa: F821
        f"UPDATE {QUEUE} SET {sets} WHERE track_id = :track_id AND version = :version AND route = :route",
        args={**cols, "track_id": track_id, "version": version, "route": route},
    )


def log(row, event: str, detail: dict | str = "", job_id: str | None = None) -> None:
    """One audit row per state change: who, what, which job, when."""
    spark.sql(  # noqa: F821
        f"INSERT INTO {EVENTS} VALUES (:track_id, :version, :route, :job_id, :event, :detail, current_timestamp())",
        args={
            "track_id": row.track_id, "version": row.version, "route": row.route,
            "job_id": job_id or row.job_id or "", "event": event,
            "detail": detail if isinstance(detail, str) else json.dumps(detail),
        },
    )


def free_slots() -> int:
    """How many new renders may start now, given the 3-at-once and 20-per-day limits."""
    running = spark.table(QUEUE).where("status = 'running' AND route IN ('mcp', 'a2a') AND skill <> 'preview_chorus'").count()  # noqa: F821
    today = spark.sql(  # noqa: F821
        f"SELECT count(*) n FROM {EVENTS} WHERE event = 'started' AND at > current_timestamp() - INTERVAL 24 HOURS"
    ).first().n
    return max(0, min(MAX_RUNNING - running, DAILY_LIMIT - today))


def save(url: str, target: str) -> str:
    """Stream a Spatial9 download link straight into a Volume."""
    import requests
    with requests.get(url, stream=True, timeout=900) as r:
        r.raise_for_status()
        with open(target, "wb") as out:
            for chunk in r.iter_content(1 << 20):
                out.write(chunk)
    return target

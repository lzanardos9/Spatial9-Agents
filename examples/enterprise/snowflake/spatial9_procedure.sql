-- SPATIAL9_RUN: a Python stored procedure that finishes running renders and starts new ones.
-- Callable from SQL, a Task, or as a custom tool for a Cortex Agent.
USE SCHEMA MEDIA.SPATIAL;

CREATE OR REPLACE PROCEDURE SPATIAL9_RUN(MAX_RUNNING NUMBER DEFAULT 3)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'requests')
HANDLER = 'run'
EXTERNAL_ACCESS_INTEGRATIONS = (spatial9_access)
SECRETS = ('key' = spatial9_key)
EXECUTE AS OWNER
AS
$$
import itertools, json, requests, _snowflake

URL = "https://spatial9.ai/mcp"
DONE = {"completed", "failed", "cancelled"}


class Client:
    """Same handshake as shared/spatial9_mcp.py, inlined because procedures cannot import local files."""

    def __init__(self, key):
        self.h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                  "Accept": "application/json, text/event-stream"}
        self.ids = itertools.count(1)
        self.post({"jsonrpc": "2.0", "id": next(self.ids), "method": "initialize",
                   "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                              "clientInfo": {"name": "spatial9-snowflake", "version": "1.0.0"}}})
        self.post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def post(self, body):
        r = requests.post(URL, json=body, headers=self.h, timeout=120)
        r.raise_for_status()
        if r.headers.get("Mcp-Session-Id"):
            self.h["Mcp-Session-Id"] = r.headers["Mcp-Session-Id"]      # echo the session
            self.h["MCP-Protocol-Version"] = "2025-06-18"
        if "id" not in body or r.status_code == 202:
            return {}
        if "text/event-stream" in r.headers.get("Content-Type", ""):
            data = [l[5:].strip() for l in r.text.splitlines() if l.startswith("data:") and l[5:].strip()]
            return json.loads(data[-1])                                   # last message is the answer
        return r.json()

    def call(self, name, args):
        reply = self.post({"jsonrpc": "2.0", "id": next(self.ids), "method": "tools/call",
                           "params": {"name": name, "arguments": args}})
        if "error" in reply:
            raise RuntimeError(reply["error"]["message"])
        result = reply.get("result", {})
        if result.get("isError"):
            raise RuntimeError(result["content"][0]["text"])          # plain-language reason
        return result.get("structuredContent", {})


def run(session, max_running):
    s9 = Client(_snowflake.get_generic_secret_string("key"))
    q = "MEDIA.SPATIAL.RENDERS_QUEUE"
    report = {"finished": 0, "started": 0, "errors": []}

    # 1. Update rows that are already running.
    for row in session.sql(f"SELECT TRACK_ID, VERSION, JOB_ID FROM {q} WHERE STATUS = 'running'").collect():
        job = s9.call("get_job_status", {"job_id": row["JOB_ID"]})
        status = job["status"] if job["status"] in DONE else "running"
        downloads = s9.call("get_downloads", {"job_id": row["JOB_ID"]}).get("downloads", []) if status == "completed" else []
        session.sql(
            f"UPDATE {q} SET STATUS = ?, STAGE = ?, DOWNLOADS = PARSE_JSON(?), ERROR = ?, UPDATED_AT = CURRENT_TIMESTAMP() "
            "WHERE TRACK_ID = ? AND VERSION = ?",
            params=[status, job.get("stage"), json.dumps(downloads), job.get("error"), row["TRACK_ID"], row["VERSION"]],
        ).collect()
        report["finished"] += status in DONE

    # 2. Start new renders up to the limit of 3 at once.
    running = session.sql(f"SELECT COUNT(*) N FROM {q} WHERE STATUS = 'running'").collect()[0]["N"]
    free = max(int(max_running) - running, 0)
    pending = session.sql(
        f"SELECT TRACK_ID, VERSION, TITLE, SOURCE_URL, STYLE FROM {q} WHERE STATUS = 'pending' LIMIT {free}"
    ).collect()
    for row in pending:
        try:
            job = s9.call("create_spatial_audio", {
                "source_url": row["SOURCE_URL"], "media_type": "music", "title": row["TITLE"],
                "style": row["STYLE"] or "live_concert", "include_binaural": True,
                "idempotency_key": f"snowflake-{row['TRACK_ID']}-v{row['VERSION']}",
            })
            session.sql(
                f"UPDATE {q} SET STATUS = 'running', JOB_ID = ?, UPDATED_AT = CURRENT_TIMESTAMP() WHERE TRACK_ID = ? AND VERSION = ?",
                params=[job["job_id"], row["TRACK_ID"], row["VERSION"]],
            ).collect()
            report["started"] += 1
        except RuntimeError as e:
            report["errors"].append({"track_id": row["TRACK_ID"], "reason": str(e)})
            if "limit" in str(e).lower():
                break
    return report
$$;

-- 2. Run it every 15 minutes with a Task.
CREATE OR REPLACE TASK SPATIAL9_EVERY_15_MIN
  WAREHOUSE = TRANSFORM_XS
  SCHEDULE = 'USING CRON */15 * * * * UTC'
AS
  CALL SPATIAL9_RUN(3);

ALTER TASK SPATIAL9_EVERY_15_MIN RESUME;

-- Try it by hand first:
-- CALL SPATIAL9_RUN(3);

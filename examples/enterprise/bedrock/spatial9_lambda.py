# AWS Lambda used by the Step Functions state machine (and usable as a Bedrock Agents action group).
# Package with requests and ../shared/spatial9_mcp.py. Set SECRET_ID and BUCKET as environment variables.
import json
import os

import boto3
import requests

from spatial9_mcp import Spatial9MCP, Spatial9Error

secrets = boto3.client("secretsmanager")
s3 = boto3.client("s3")
_key = None


def client() -> Spatial9MCP:
    global _key
    if _key is None:                          # cache the secret for warm invocations
        _key = json.loads(secrets.get_secret_value(SecretId=os.environ["SECRET_ID"])["SecretString"])["api_key"]
    return Spatial9MCP(api_key=_key)


def start(event):
    job = client().call("create_spatial_audio", {
        "source_url": event["source_url"],
        "media_type": "music",
        "title": event["title"],
        "style": event.get("style", "live_concert"),
        "include_binaural": True,
        "idempotency_key": f"aws-{event['track_id']}-v{event.get('version', 1)}",
    })
    return {**event, "job_id": job["job_id"]}


def status(event):
    job = client().call("get_job_status", {"job_id": event["job_id"]})
    return {**event, "status": job["status"], "stage": job.get("stage"), "error": job.get("error")}


def save(event):
    keys = []
    for f in client().downloads(event["job_id"]):
        key = f"immersive/{event['track_id']}/{f['filename']}"
        with requests.get(f["url"], stream=True, timeout=600) as r:
            r.raise_for_status()
            s3.upload_fileobj(r.raw, os.environ["BUCKET"], key)
        keys.append(key)
    return {**event, "s3_keys": keys}


ACTIONS = {"start": start, "status": status, "save": save}


def handler(event, _context):
    """Step Functions sends {"action": "start" | "status" | "save", ...track fields}."""
    try:
        return ACTIONS[event["action"]](event)
    except Spatial9Error as e:                # plain-language reason, safe to show in the console
        return {**event, "status": "failed", "error": str(e)}

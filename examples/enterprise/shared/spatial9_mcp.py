"""Minimal Spatial9 MCP client for enterprise jobs (Databricks, Snowflake, Cloud Run, Lambda).

It speaks the MCP Streamable HTTP transport with nothing but `requests`:
  1. initialize                    -> the server may answer with an Mcp-Session-Id header
  2. notifications/initialized     -> tells the server we are ready
  3. tools/call                    -> one call per Spatial9 tool

Usage:
    client = Spatial9MCP(api_key=secret_from_your_vault)
    job = client.call("create_spatial_audio", {...})
"""
from __future__ import annotations

import itertools
import json
import time

import requests

DONE = {"completed", "failed", "cancelled"}
PROTOCOL_VERSION = "2025-06-18"


class Spatial9Error(RuntimeError):
    """Raised when the server or a tool refuses a request. The message is safe to log."""


class Spatial9MCP:
    def __init__(self, api_key: str, url: str = "https://spatial9.ai/mcp", timeout: int = 120):
        self.url = url
        self.timeout = timeout
        self.session_id: str | None = None
        self._ids = itertools.count(1)
        self.headers = {
            "Authorization": f"Bearer {api_key}",       # s9_... key, always read from a secret store
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",  # the server may reply with either
        }
        self._initialize()

    # ---------- transport ----------

    def _post(self, payload: dict) -> dict | None:
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id   # echo the session on every later request
            headers["MCP-Protocol-Version"] = PROTOCOL_VERSION
        r = requests.post(self.url, json=payload, headers=headers, timeout=self.timeout)
        if r.status_code == 401:
            raise Spatial9Error("Spatial9 rejected the key. Check the secret or create a new key.")
        r.raise_for_status()
        self.session_id = r.headers.get("Mcp-Session-Id", self.session_id)
        if "id" not in payload or r.status_code == 202:   # notifications get no body
            return None
        return self._parse(r)

    @staticmethod
    def _parse(r: requests.Response) -> dict:
        """Read a plain JSON reply or the last JSON-RPC message of a text/event-stream reply."""
        if "text/event-stream" not in r.headers.get("Content-Type", ""):
            return r.json()
        message = None
        for line in r.text.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk:
                    message = json.loads(chunk)
        if message is None:
            raise Spatial9Error("The server sent an empty stream.")
        return message

    def _initialize(self) -> None:
        self._post({
            "jsonrpc": "2.0", "id": next(self._ids), "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "spatial9-enterprise", "version": "1.0.0"},
            },
        })
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    # ---------- tools ----------

    def call(self, name: str, arguments: dict) -> dict:
        """Call one tool and return its structuredContent."""
        reply = self._post({
            "jsonrpc": "2.0", "id": next(self._ids), "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }) or {}
        if "error" in reply:                      # protocol problem, such as a bad parameter
            raise Spatial9Error(reply["error"].get("message", "MCP error"))
        result = reply.get("result", {})
        if result.get("isError"):                 # the tool refused and explains why in plain words
            raise Spatial9Error(result["content"][0]["text"])
        return result.get("structuredContent", {})

    def wait(self, job_id: str, every: int = 45, max_minutes: int = 60) -> dict:
        """Poll get_job_status every 30 to 60 seconds. Songs usually take 10 to 20 minutes."""
        deadline = time.time() + max_minutes * 60
        while time.time() < deadline:
            job = self.call("get_job_status", {"job_id": job_id})
            if job.get("status") in DONE:
                return job
            time.sleep(every)
        raise Spatial9Error(f"Job {job_id} is still running after {max_minutes} minutes.")

    def downloads(self, job_id: str, keep=("binaural", "youtube_video", "iamf")) -> list[dict]:
        """Only links returned by Spatial9. Never build download URLs yourself."""
        files = self.call("get_downloads", {"job_id": job_id}).get("downloads", [])
        return [f for f in files if f.get("id") in keep]

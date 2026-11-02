"""Minimal Spatial9 Agent2Agent (A2A 0.3.0) client for enterprise jobs.

A2A hands a whole task to the Spatial9 agent at https://spatial9.ai/a2a and lets you follow it:
  message/send   -> returns a task right away (state: submitted)
  tasks/get      -> poll every 30 to 60 seconds until completed, failed or canceled
  tasks/cancel   -> stop a task (refunded if paid processing had not started)

The messageId doubles as the idempotency key: sending the same one again returns the same task.

Usage:
    a2a = Spatial9A2A(api_key=secret_from_your_vault)
    task = a2a.send("stems-track-042-v1", skill="split_stems", data={"upload_id": "..."})
    task = a2a.get(task["id"])
"""
from __future__ import annotations

import itertools

import requests

FINAL = {"completed", "failed", "canceled", "rejected"}
SKILLS = {"spatial_audio", "split_stems", "convert_dolby", "preview_chorus", "upload_link"}


class Spatial9A2AError(RuntimeError):
    """Raised when the agent refuses a request. The message is safe to log."""


class Spatial9A2A:
    def __init__(self, api_key: str, url: str = "https://spatial9.ai/a2a", timeout: int = 60):
        self.url = url
        self.timeout = timeout
        self._ids = itertools.count(1)
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    def _rpc(self, method: str, params: dict) -> dict:
        r = requests.post(
            self.url,
            json={"jsonrpc": "2.0", "id": next(self._ids), "method": method, "params": params},
            headers=self.headers,
            timeout=self.timeout,
        )
        if r.status_code == 401:
            raise Spatial9A2AError("Spatial9 rejected the key. Check the secret or create a new key.")
        r.raise_for_status()
        body = r.json()
        if "error" in body:
            raise Spatial9A2AError(body["error"].get("message", "A2A error"))
        return body["result"]

    def send(self, message_id: str, skill: str, data: dict, text: str = "") -> dict:
        """Start a task. data holds source_url or upload_id plus options such as title or style."""
        if skill not in SKILLS:
            raise ValueError(f"Unknown Spatial9 skill: {skill}")
        parts = [{"kind": "data", "data": {"skill": skill, **data}}]
        if text:
            parts.insert(0, {"kind": "text", "text": text})
        return self._rpc("message/send", {
            "message": {"kind": "message", "role": "user", "messageId": message_id, "parts": parts},
        })

    def get(self, task_id: str) -> dict:
        return self._rpc("tasks/get", {"id": task_id, "historyLength": 0})

    def cancel(self, task_id: str) -> dict:
        return self._rpc("tasks/cancel", {"id": task_id})

    def set_webhook(self, task_id: str, url: str, token: str) -> dict:
        """Optional: Spatial9 posts the task to this https URL on every state change.
        Your endpoint must check the X-A2A-Notification-Token header against token."""
        return self._rpc("tasks/pushNotificationConfig/set", {
            "taskId": task_id,
            "pushNotificationConfig": {"url": url, "token": token},
        })

    @staticmethod
    def state(task: dict) -> str:
        return task.get("status", {}).get("state", "unknown")

    @staticmethod
    def files(task: dict) -> list[dict]:
        """Download links from the task artifacts. Never build download URLs yourself."""
        out = []
        for artifact in task.get("artifacts", []):
            for part in artifact.get("parts", []):
                f = part.get("file") if part.get("kind") == "file" else None
                if f and f.get("uri"):
                    out.append({"name": f.get("name") or artifact.get("name", "file"), "url": f["uri"]})
        return out

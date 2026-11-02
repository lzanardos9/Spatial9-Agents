"""Spatial9 pipeline: render every WAV in a folder to immersive Eclipsa Audio.

Usage:  SPATIAL9_KEY=s9_... python spatial9_pipeline.py masters/ out/
"""
import os, re, sys, time, pathlib
from concurrent.futures import ThreadPoolExecutor
import requests

MCP_URL = "https://spatial9.ai/mcp"      # account server; https://spatial9.ai/mcp/free is the guest server
KEY = os.environ["SPATIAL9_KEY"]          # personal key from spatial9.ai/connect, never hard-code it
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",   # MCP clients announce both
}
DONE = {"completed", "failed", "cancelled"}
KEEP = {"binaural", "youtube_video", "iamf"}         # download ids we want to save


def call_tool(name: str, arguments: dict) -> dict:
    """Send one MCP tools/call and return its structuredContent."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}}
    r = requests.post(MCP_URL, json=body, headers=HEADERS, timeout=120)
    r.raise_for_status()                          # 401 means the key is wrong or revoked
    reply = r.json()
    if "error" in reply:                          # protocol problem, such as a bad parameter
        raise RuntimeError(reply["error"]["message"])
    result = reply["result"]
    if result.get("isError"):                     # the tool refused and says why in plain words
        raise RuntimeError(result["content"][0]["text"])
    return result.get("structuredContent", {})


def upload(path: pathlib.Path) -> str:
    """Local file -> upload_id. Links last 2 hours and accept files up to 2 GB."""
    link = call_tool("create_upload_link", {"filename": path.name, "media_type": "music"})
    with path.open("rb") as f:
        requests.put(link["direct_upload_url"], data=f,
                     headers={"Content-Type": "audio/wav"}, timeout=3600).raise_for_status()
    return link["upload_id"]


def wait_for(job_id: str, every: int = 45) -> dict:
    """Poll every 30 to 60 seconds until the job finishes. Songs take 10 to 20 minutes."""
    while True:
        job = call_tool("get_job_status", {"job_id": job_id})
        print(f"  {job.get('title')}: {job.get('stage')} {job.get('progress', 0)}%")
        if job["status"] in DONE:
            return job
        time.sleep(every)


def render(path: pathlib.Path, out_dir: pathlib.Path, style: str = "live_concert") -> None:
    slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    job = call_tool("create_spatial_audio", {
        "upload_id": upload(path),
        "media_type": "music",
        "title": path.stem.replace("-", " ").title(),
        "style": style,                        # live_concert, club, cinema or intimate_studio
        "include_binaural": True,              # always ship a headphone version
        "idempotency_key": f"pipeline-{slug}", # a retry returns the same job, never a second charge
    })
    job = wait_for(job["job_id"])
    if job["status"] != "completed":
        print(f"  {path.name}: {job['status']} (failed renders are refunded)")
        return
    files = call_tool("get_downloads", {"job_id": job["job_id"]})["downloads"]
    for f in files:
        if f["id"] in KEEP:                    # only real links returned by Spatial9
            target = out_dir / f["filename"]
            target.write_bytes(requests.get(f["url"], timeout=600).content)
            print(f"  saved {target}")


if __name__ == "__main__":
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    # Three workers match the limit of three renders at once.
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(lambda p: render(p, out), sorted(src.glob("*.wav"))))

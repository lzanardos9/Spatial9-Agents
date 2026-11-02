from datetime import datetime
from airflow.decorators import dag, task


@dag(schedule="@daily", start_date=datetime(2026, 1, 1), catchup=False)
def spatial9_catalog():

    @task
    def pending_tracks() -> list[dict]:
        # Read up to 20 tracks a day (the daily limit) still marked "pending".
        # Replace with your warehouse query: Snowflake, BigQuery, Postgres...
        return [{"isrc": "USABC2600001", "title": "Night Drive",
                 "url": "https://cdn.example.com/masters/USABC2600001.wav"}]

    @task(pool="spatial9", retries=2)
    def render(track: dict) -> dict:
        from spatial9_pipeline import call_tool, wait_for   # reuse the commented helpers
        job = call_tool("create_spatial_audio", {
            "source_url": track["url"], "media_type": "music", "title": track["title"],
            "include_binaural": True,
            "idempotency_key": f"catalog-{track['isrc']}",   # ISRC = one render per recording
        })
        done = wait_for(job["job_id"])
        if done["status"] != "completed":
            raise RuntimeError(f"{track['title']}: {done['status']}")
        files = call_tool("get_downloads", {"job_id": done["job_id"]})["downloads"]
        return {"isrc": track["isrc"], "files": {f["id"]: f["url"] for f in files}}

    @task
    def record(results: list[dict]) -> None:
        # Write the links back and set each track to "ready for review".
        for r in results:
            print(r["isrc"], r["files"].get("binaural"))

    record(render.expand(track=pending_tracks()))


spatial9_catalog()

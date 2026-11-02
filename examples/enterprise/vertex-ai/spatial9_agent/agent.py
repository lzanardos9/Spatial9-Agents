# Vertex AI agent (Google ADK) that uses Spatial9 tools over MCP.
# pip install "google-adk>=1.0" google-cloud-secret-manager
# Local test:  adk web   (from the folder that contains this package)
import os

from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.cloud import secretmanager


def spatial9_key() -> str:
    """Read the s9_ key from Secret Manager. The agent's service account needs secretAccessor."""
    name = f"projects/{os.environ['GOOGLE_CLOUD_PROJECT']}/secrets/spatial9-api-key/versions/latest"
    return secretmanager.SecretManagerServiceClient().access_secret_version(name=name).payload.data.decode()


spatial9 = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="https://spatial9.ai/mcp",
        headers={"Authorization": f"Bearer {spatial9_key()}"},
        timeout=60,
        sse_read_timeout=600,
    ),
    # Expose only what this agent needs. Leave out publish_to_youtube for an internal catalog bot.
    tool_filter=[
        "create_upload_link", "create_spatial_audio", "create_from_stems",
        "get_job_status", "get_downloads", "preview_chorus", "split_stems",
    ],
)

root_agent = LlmAgent(
    name="spatial9_catalog_agent",
    model="gemini-2.5-flash",
    instruction=(
        "You help the catalog team make immersive versions of songs with Spatial9. "
        "Only render music the team says it owns. Always send an idempotency_key built from the track id. "
        "Start at most 3 renders at once. Songs take 10 to 20 minutes: tell the user, then check "
        "get_job_status when asked. Only share links returned by get_downloads."
    ),
    tools=[spatial9],
)

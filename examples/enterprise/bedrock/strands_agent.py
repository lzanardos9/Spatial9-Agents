# Amazon Bedrock agent built with Strands Agents, using Spatial9 tools over MCP.
# pip install strands-agents mcp boto3
import json

import boto3
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient


def spatial9_key() -> str:
    """The s9_ key lives in AWS Secrets Manager as {"api_key": "s9_..."}."""
    raw = boto3.client("secretsmanager").get_secret_value(SecretId="spatial9/api-key")["SecretString"]
    return json.loads(raw)["api_key"]


spatial9 = MCPClient(lambda: streamablehttp_client(
    "https://spatial9.ai/mcp",
    headers={"Authorization": f"Bearer {spatial9_key()}"},
))

SYSTEM = (
    "You help the catalog team make immersive versions of songs with Spatial9. "
    "Only render music the team owns. Always send an idempotency_key built from the track id. "
    "At most 3 renders at once. Only share links returned by get_downloads."
)

with spatial9:                                    # the MCP session stays open inside this block
    tools = [t for t in spatial9.list_tools_sync()
             if t.tool_name != "publish_to_youtube"]   # keep public publishing out of this bot
    agent = Agent(
        model=BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0"),
        system_prompt=SYSTEM,
        tools=tools,
    )
    agent("Make an immersive live concert version of https://example.com/masters/track-0042.wav "
          "titled 'Northern Lights', track id 0042, and tell me the job id.")

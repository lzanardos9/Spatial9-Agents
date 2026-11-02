# Spatial9 for enterprise platforms

Governed catalog renders from the data and AI platforms enterprises already run. Every recipe follows the same rules: key in the platform's secret store, at most 3 renders at once, an `idempotency_key` per track and version, and results written back for audit.

| Platform | Folder | Pattern |
|---|---|---|
| Databricks | [databricks](databricks/README.md) | Unity Catalog connection, Lakeflow Job, Volumes, optional AI Gateway MCP Services |
| Databricks Solutions Accelerator | [databricks/solution-accelerator](databricks/solution-accelerator/README.md) | Asset Bundle with Auto Loader, MCP, A2A and REST API routes, audit table and gold views |
| Snowflake | [snowflake](snowflake/README.md) | External access integration, Python procedure, Task, Cortex Agent custom tool |
| Google Cloud and Vertex AI | [vertex-ai](vertex-ai/README.md) | ADK agent with `McpToolset`, Agent Engine, Cloud Run job and Scheduler, BigQuery |
| AWS and Amazon Bedrock | [bedrock](bedrock/README.md) | Strands agent, Lambda, Step Functions, S3, AgentCore Gateway |
| Any Python runtime | [shared/spatial9_mcp.py](shared/spatial9_mcp.py) | The MCP handshake with `requests` only |
| Any Python runtime | [shared/spatial9_a2a.py](shared/spatial9_a2a.py) | Agent2Agent tasks: send, follow, cancel, webhooks |

Other orchestrators such as Prefect, Dagster, Salesforce Agentforce, ServiceNow and IBM watsonx Orchestrate can reuse `shared/spatial9_mcp.py` or connect to `https://spatial9.ai/mcp` as a remote MCP server where they support one.

Microsoft Fabric is not supported.

Guide: https://spatial9.ai/blog/spatial9-enterprise-agents-databricks-snowflake-vertex-bedrock

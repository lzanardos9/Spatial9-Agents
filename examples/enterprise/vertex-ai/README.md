# Spatial9 on Google Cloud and Vertex AI

Two ways to use Spatial9 on Google Cloud: an agent your team talks to, or a scheduled job with no agent.

| File | What it does |
|---|---|
| [spatial9_agent/agent.py](spatial9_agent/agent.py) | ADK agent with Spatial9 tools through `McpToolset`, key from Secret Manager |
| [deploy_agent_engine.py](deploy_agent_engine.py) | Deploys that agent to Vertex AI Agent Engine |
| [batch_job.py](batch_job.py) | Cloud Run job: BigQuery queue in, Cloud Storage files out, 3 workers |
| [cloud_run_job.sh](cloud_run_job.sh) | Secret, job and Cloud Scheduler setup |

## Notes

- Use `tool_filter` to give each agent only the tools it needs.
- ADK can also expose an agent over A2A. Spatial9 has its own A2A endpoint at `https://spatial9.ai/a2a` if you prefer agent-to-agent tasks over tool calls.
- The Agent Engine SDK changes often. Pin versions and check the current Google docs before deploying.

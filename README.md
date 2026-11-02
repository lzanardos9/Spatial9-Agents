# Spatial9 Agent Skills

Agent Skills (SKILL.md format) and ready-to-run workflow examples that teach AI agents to use the Spatial9 immersive audio engine. They work in Claude, Claude Code, OpenAI Codex, GitHub Copilot, Cursor, Gemini CLI and any agent that reads the Agent Skills standard.

Every skill uses the Spatial9 MCP server:

- `https://spatial9.ai/mcp`: sign in with OAuth, or send `Authorization: Bearer s9_...` (create a key at https://spatial9.ai/connect)
- `https://spatial9.ai/mcp/free`: free guest allowance, no sign-in

## Skills

| Skill | What the agent can do |
|---|---|
| [spatial9-immersive-mix](spatial9-immersive-mix/SKILL.md) | Song, stems or video to Eclipsa Audio (IAMF) with a binaural headphone version |
| [spatial9-stem-split](spatial9-stem-split/SKILL.md) | Separate a song into instrument stems |
| [spatial9-atmos-to-eclipsa](spatial9-atmos-to-eclipsa/SKILL.md) | Convert Dolby or ADM BWF masters to Eclipsa Audio |
| [spatial9-chorus-preview](spatial9-chorus-preview/SKILL.md) | Free 30-second headphone preview of the chorus |
| [spatial9-remix-by-voice](spatial9-remix-by-voice/SKILL.md) | Move, level, animate and add effects to a mix from plain language |
| [spatial9-release-publisher](spatial9-release-publisher/SKILL.md) | Publish to YouTube and make 9:16 social clips |
| [spatial9-enterprise-catalog](spatial9-enterprise-catalog/SKILL.md) | Governed catalog renders from Databricks, Snowflake, Vertex AI and Bedrock |

## Install

1. Connect the server. For Claude Code, run [examples/setup/claude-code.sh](examples/setup/claude-code.sh). For apps that read an `mcpServers` file, use [examples/setup/mcp.json](examples/setup/mcp.json).
2. Copy a skill folder into your agent's skills folder, for example `.claude/skills/` for a project or `~/.claude/skills/` for your user. Other agents use their own skills folder.
3. Ask in plain words: "Make my song immersive", "Split this into stems", "Preview the chorus in 3D".

## Workflow examples

| Folder | What it shows |
|---|---|
| [examples/python](examples/python/spatial9_pipeline.py) | Commented batch pipeline: upload, render with 3 workers, download |
| [examples/node](examples/node/a2a-webhook.mjs) | Start an A2A task and get a webhook when it finishes |
| [examples/n8n](examples/n8n/README.md) | Form to Slack workflow with HTTP Request nodes, or an AI Agent with the MCP Client Tool |
| [examples/zapier](examples/zapier/README.md) | Two Zaps with a catch hook, plus the Make version |
| [examples/power-automate](examples/power-automate/README.md) | A "Do until" loop for Microsoft 365 teams |
| [examples/github-actions](examples/github-actions/spatial9.yml) | Render whenever a master is pushed |
| [examples/airflow](examples/airflow/spatial9_catalog_dag.py) | Nightly catalog job with a pool of 3 |
| [examples/enterprise](examples/enterprise/README.md) | Databricks, Snowflake, Google Vertex AI and Amazon Bedrock recipes with a shared MCP client |
| [examples/open-source](examples/open-source/README.md) | MinIO, Kafka, PostgreSQL, FFmpeg, FastAPI and Dagster pipeline with real-time A2A webhooks and a live preview page |

## Write your own skill

Start from [templates/SKILL.template.md](templates/SKILL.template.md). Keep the `description` specific about when to use the skill, list the exact tool names, and include the rules your team cares about.

## Limits worth knowing

- Up to 3 renders at once and 20 per day per account.
- A failed render refunds its project automatically.
- Upload links last 2 hours and accept files up to 2 GB.
- Always send an `idempotency_key` so a retry never starts a second render.

## Learn more

- Full guide: https://spatial9.ai/blog/spatial9-agent-skills-pipelines-n8n-workflows
- Enterprise guide: https://spatial9.ai/blog/spatial9-enterprise-agents-databricks-snowflake-vertex-bedrock
- Open source pipeline guide: https://spatial9.ai/blog/open-source-spatial-audio-pipeline-real-time-spatial9
- Browse these files online: https://spatial9.ai/agents/skills
- A2A agents: https://spatial9.ai/agents

## License

MIT. See [LICENSE](LICENSE).

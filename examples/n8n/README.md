# n8n

## Option A: a fixed workflow with HTTP Request nodes

Anyone on your team pastes a song link into a form and receives immersive files in Slack.

1. **Credential:** create a "Header Auth" credential named Spatial9 with the name `Authorization` and the value `Bearer s9_your_key`. Never type the key into a node.
2. **Form Trigger:** fields for Song link, Title and Style.
3. **HTTP Request, "Start render":** method POST, URL `https://spatial9.ai/mcp`, authentication from the Spatial9 credential, an `Accept` header of `application/json, text/event-stream`, and the body in [start-render.body.js](start-render.body.js).
4. **Wait:** 60 seconds.
5. **HTTP Request, "Check status":** the same settings, with the body in [check-status.body.js](check-status.body.js).
6. **Switch:** route on `{{ $json.result.structuredContent.status }}`. `completed` continues, `failed` or `cancelled` goes to an alert, anything else loops back to Wait.
7. **HTTP Request, "Get downloads":** calls `get_downloads`. A Code node with [format-downloads.code-node.js](format-downloads.code-node.js) picks the links, then Google Drive and Slack nodes use them.

## Option B: an AI Agent node with the MCP Client Tool

For open-ended requests, add an **AI Agent** node, attach a chat model, and attach the **MCP Client Tool** node with:

- **Endpoint:** `https://spatial9.ai/mcp`
- **Server transport:** HTTP Streamable
- **Authentication:** Bearer, using your Spatial9 key
- **Tools to include:** "Selected", for example `preview_chorus`, `get_clip`, `create_spatial_audio`, `get_job_status` and `get_downloads`

Paste the steps and rules from the matching `SKILL.md` into the agent's system message. Leave publishing tools out of unattended agents.

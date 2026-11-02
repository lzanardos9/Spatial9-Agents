# Power Automate

The HTTP action is a premium connector. A typical flow starts when a SharePoint list item with a song link is created:

1. **HTTP "Start render":** POST to `https://spatial9.ai/mcp` with the `tools/call` body for `create_spatial_audio`. Store the key in Azure Key Vault or a secure environment variable.
2. **Do until** the status equals `completed`, with a count limit of 40 and a timeout of `PT1H`. Inside it, a **Delay** of 1 minute and an **HTTP "Check status"** call to `get_job_status`.
3. **HTTP "Get downloads"**, then update the list item and post the links to Teams.

The expression that reads the status inside the loop is in [status-expression.txt](status-expression.txt).

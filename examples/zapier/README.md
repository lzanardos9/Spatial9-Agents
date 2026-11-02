# Zapier and Make

Zapier steps should not wait 20 minutes, so both tools use the A2A webhook and two automations.

## Zapier

1. **Zap 2 first, "Render finished":** trigger "Webhooks by Zapier: Catch Hook". Copy its URL.
2. **Zap 1, "Start render":** a trigger such as a new Google Sheets row with a song link, then "Webhooks by Zapier: Custom Request" with method POST, URL `https://spatial9.ai/a2a`, headers `Authorization: Bearer s9_...` and `Content-Type: application/json`, and the same body as [../node/a2a-webhook.mjs](../node/a2a-webhook.mjs), with Zap 2's URL as `pushNotificationConfig.url`.
3. **Back in Zap 2:** a Filter that only continues when `status.state` exactly matches `completed`, then a "Code by Zapier" step with [code_by_zapier.py](code_by_zapier.py), then Gmail, Slack or Google Drive.

## Make

Scenario 1 uses a trigger (for example "Watch Rows" in Google Sheets) followed by the HTTP module "Make a request": method POST, URL `https://spatial9.ai/a2a`, an `Authorization` header, body type "Raw" with content type JSON, and the A2A body with the webhook URL from Scenario 2.

Scenario 2 starts with a "Custom webhook", filters on `status.state = completed`, uses an Iterator over `artifacts`, downloads each `file.uri` with "Get a file", and uploads it to Dropbox, Box or Google Drive.

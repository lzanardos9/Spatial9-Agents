# Spatial9 on AWS and Amazon Bedrock

| File | What it does |
|---|---|
| [strands_agent.py](strands_agent.py) | Bedrock agent built with Strands Agents, Spatial9 tools through `MCPClient` |
| [spatial9_lambda.py](spatial9_lambda.py) | Lambda with `start`, `status` and `save` actions, key from Secrets Manager, files to S3 |
| [state_machine.json](state_machine.json) | Step Functions Map: 3 renders at a time, poll every 45 seconds |

## Run it

1. Store the key: `aws secretsmanager create-secret --name spatial9/api-key --secret-string '{"api_key":"s9_..."}'`
2. Deploy `spatial9_lambda.py` (with `spatial9_mcp.py` and `requests`) as a function named `spatial9`. Give it read access to the secret and write access to the bucket.
3. Create the state machine from `state_machine.json` and start it with `{"tracks": [{"track_id": "0042", "title": "Northern Lights", "source_url": "https://..."}]}`.

## Bedrock AgentCore and Bedrock Agents

- AgentCore Runtime can host the Strands agent. AgentCore Gateway can front Spatial9 as an MCP target so many agents share one governed connection, with AgentCore Identity holding the key.
- Classic Bedrock Agents can call the same Lambda as an action group.
- Service names and console steps change often. Check the current AWS docs before you deploy.

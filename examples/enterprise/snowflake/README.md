# Spatial9 on Snowflake

Render tracks listed in a Snowflake table, with outbound access locked to `spatial9.ai` and the key stored as a Snowflake secret.

| File | What it does |
|---|---|
| [setup.sql](setup.sql) | Network rule, secret, external access integration, queue table and stage |
| [spatial9_procedure.sql](spatial9_procedure.sql) | `SPATIAL9_RUN` Python procedure with the MCP handshake, plus a Task every 15 minutes |

## Run it

1. Run `setup.sql`, replacing `s9_replace_me` with your key.
2. Run `spatial9_procedure.sql`.
3. Insert rows into `RENDERS_QUEUE` with a presigned `SOURCE_URL` for each master.
4. `CALL SPATIAL9_RUN(3);` returns a small report of renders started and finished.

## Cortex Agents

Snowflake's own MCP server feature publishes Snowflake data to outside agents. It does not call outside servers. To let a Cortex Agent start renders, add `SPATIAL9_RUN` (or a smaller procedure per tool) as a custom tool. The agent then works through the same network rule, secret and grants.

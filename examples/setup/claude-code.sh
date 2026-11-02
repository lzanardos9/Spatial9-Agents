# Create a personal key at https://spatial9.ai/connect, then keep it in an environment variable.
export SPATIAL9_KEY="s9_your_key_here"

# Claude Code: register Spatial9 as a remote MCP server over HTTP.
claude mcp add --transport http spatial9 https://spatial9.ai/mcp \
  --header "Authorization: Bearer $SPATIAL9_KEY"

# No account yet? Use the free guest server instead (no key needed).
claude mcp add --transport http spatial9-free https://spatial9.ai/mcp/free

{{ JSON.stringify({
  jsonrpc: "2.0", id: 2, method: "tools/call",
  params: {
    name: "get_job_status",
    arguments: { job_id: $('Start render').item.json.result.structuredContent.job_id }
  }
}) }}

{{ JSON.stringify({
  jsonrpc: "2.0",
  id: 1,
  method: "tools/call",
  params: {
    name: "create_spatial_audio",
    arguments: {
      source_url: $json["Song link"],          // a direct https link to the audio file
      media_type: "music",
      title: $json["Title"],
      style: $json["Style"] || "live_concert",
      include_binaural: true,
      // Same title = same key = same job, so a re-run never double-charges.
      idempotency_key: "n8n-" + $json["Title"].toLowerCase().replace(/[^a-z0-9]+/g, "-")
    }
  }
}) }}

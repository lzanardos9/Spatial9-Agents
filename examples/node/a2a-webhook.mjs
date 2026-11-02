// Start a Spatial9 render and ask Spatial9 to call us back when it changes.
const res = await fetch("https://spatial9.ai/a2a", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${process.env.SPATIAL9_KEY}`,   // s9_ key from a secret store
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    jsonrpc: "2.0",
    id: "start-1",
    method: "message/send",
    params: {
      message: {
        kind: "message",
        role: "user",
        messageId: "night-drive-001",          // doubles as the idempotency key
        parts: [{
          kind: "data",
          data: {
            skill: "spatial_audio",            // or split_stems, convert_dolby, preview_chorus
            source_url: "https://example.com/masters/night-drive.wav",
            title: "Night Drive",
            style: "cinema",
          },
        }],
      },
      configuration: {
        pushNotificationConfig: {
          url: "https://hooks.example.com/spatial9-updates",  // https, public host, port 443
          token: process.env.WEBHOOK_TOKEN,                    // echoed in X-A2A-Notification-Token
        },
      },
    },
  }),
});

const body = await res.json();
if (body.error) throw new Error(body.error.message);   // never assume the call worked
console.log("Task", body.result.id, "is", body.result.status.state);

// n8n Code node: turn the Spatial9 download list into a Slack-friendly message.
const result = $input.first().json.result;
if (result.isError) throw new Error(result.content[0].text);   // surface Spatial9's own message

const files = result.structuredContent.downloads ?? [];
const wanted = files.filter(f => ["binaural", "youtube_video", "iamf"].includes(f.id));
const lines = wanted.map(f => `• ${f.label}: ${f.url}`);

return [{ json: { text: `Your immersive mix is ready:\n${lines.join("\n")}` } }];

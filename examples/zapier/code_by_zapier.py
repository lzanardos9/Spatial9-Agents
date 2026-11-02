# Code by Zapier (Python). Input data: task = the raw JSON body from the catch hook.
import json

task = json.loads(input_data["task"])
links = []
for artifact in task.get("artifacts", []):
    for part in artifact.get("parts", []):
        if part.get("kind") == "file":           # each download arrives as a file part
            f = part["file"]
            links.append(f.get("name", "file") + ": " + f["uri"])

output = {"title": task.get("id"), "links": "\n".join(links)}

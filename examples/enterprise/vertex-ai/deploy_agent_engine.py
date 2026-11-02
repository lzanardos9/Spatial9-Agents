# Deploy the ADK agent to Vertex AI Agent Engine.
# pip install "google-cloud-aiplatform[agent_engines,adk]"
# The Agent Engine API changes between releases: pin the versions you tested with.
import vertexai
from vertexai import agent_engines

from spatial9_agent.agent import root_agent

PROJECT = "your-project"
LOCATION = "us-central1"

vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=f"gs://{PROJECT}-agent-staging")

app = agent_engines.AdkApp(agent=root_agent, enable_tracing=True)

remote = agent_engines.create(
    agent_engine=app,
    display_name="spatial9-catalog-agent",
    requirements=[
        "google-cloud-aiplatform[agent_engines,adk]",
        "google-cloud-secret-manager",
    ],
    extra_packages=["./spatial9_agent"],
    env_vars={"GOOGLE_CLOUD_PROJECT": PROJECT},
)
print("Deployed:", remote.resource_name)

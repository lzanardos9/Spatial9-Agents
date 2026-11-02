#!/usr/bin/env bash
# Nightly catalog renders on Google Cloud with no agent: a Cloud Run job plus Cloud Scheduler.
# The job runs batch_job.py, which uses ../shared/spatial9_mcp.py.
set -euo pipefail

PROJECT=your-project
REGION=us-central1
SA=spatial9-runner@${PROJECT}.iam.gserviceaccount.com

# 1. Store the key once.
printf '%s' "$SPATIAL9_KEY" | gcloud secrets create spatial9-api-key --data-file=- --project "$PROJECT"
gcloud secrets add-iam-policy-binding spatial9-api-key \
  --member "serviceAccount:${SA}" --role roles/secretmanager.secretAccessor --project "$PROJECT"

# 2. Build and create the job. The key arrives as an environment variable, never in the image.
gcloud run jobs deploy spatial9-catalog \
  --source . --region "$REGION" --project "$PROJECT" \
  --service-account "$SA" \
  --set-secrets SPATIAL9_KEY=spatial9-api-key:latest \
  --set-env-vars BUCKET=${PROJECT}-immersive \
  --task-timeout 90m --max-retries 1

# 3. Run it every night at 02:00.
gcloud scheduler jobs create http spatial9-nightly \
  --location "$REGION" --project "$PROJECT" \
  --schedule "0 2 * * *" --time-zone "Etc/UTC" \
  --uri "https://run.googleapis.com/v2/projects/${PROJECT}/locations/${REGION}/jobs/spatial9-catalog:run" \
  --http-method POST --oauth-service-account-email "$SA"

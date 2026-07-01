#!/bin/bash
# Create Cloud Scheduler jobs for the Citizens of India pipeline.
# Run once after deploying to Cloud Run.

set -euo pipefail

PROJECT="eastern-map-498917-i6"
REGION="us-east1"
BASE_URL="https://citizens-india-backend-1012823692058.us-east1.run.app"
CRON_SECRET="${CRON_SECRET:-}"  # set this env var before running

if [[ -z "$CRON_SECRET" ]]; then
  echo "ERROR: Set CRON_SECRET env var first"
  exit 1
fi

echo "Enabling Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com --project "$PROJECT"

echo "Creating weekly-analysis job (every Monday 8am IST = 2:30am UTC)..."
gcloud scheduler jobs create http citizens-india-weekly-analysis \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "30 2 * * 1" \
  --uri "$BASE_URL/cron/weekly-analysis" \
  --http-method POST \
  --headers "X-Cron-Secret=$CRON_SECRET,Content-Type=application/json" \
  --message-body '{}' \
  --time-zone "UTC" \
  --description "Weekly multi-agent analysis pipeline for all constituencies" \
  --attempt-deadline 540s \
  2>/dev/null || gcloud scheduler jobs update http citizens-india-weekly-analysis \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "30 2 * * 1" \
  --uri "$BASE_URL/cron/weekly-analysis" \
  --http-method POST \
  --headers "X-Cron-Secret=$CRON_SECRET,Content-Type=application/json" \
  --message-body '{}'

echo "Creating daily-summary job (every day 7am IST = 1:30am UTC)..."
gcloud scheduler jobs create http citizens-india-daily-summary \
  --project "$PROJECT" \
  --location "$REGION" \
  --schedule "30 1 * * *" \
  --uri "$BASE_URL/cron/daily-summary" \
  --http-method POST \
  --headers "X-Cron-Secret=$CRON_SECRET,Content-Type=application/json" \
  --message-body '{}' \
  --time-zone "UTC" \
  --description "Daily theme aggregation for all constituencies" \
  2>/dev/null || echo "daily-summary job already exists (skipped)"

echo ""
echo "Cloud Scheduler jobs created:"
gcloud scheduler jobs list --project "$PROJECT" --location "$REGION"

#!/usr/bin/env bash
# GCP project bootstrap for Citizens of India
# Run once: bash setup_gcp.sh <your-project-id> <your-gemini-api-key>
set -euo pipefail

PROJECT_ID="${1:-citizens-india-demo}"
GEMINI_KEY="${2:-}"
REGION="asia-south1"

echo "🚀 Setting up GCP project: $PROJECT_ID"

# ── Project & billing ──────────────────────────────────────────────────────────
gcloud projects create "$PROJECT_ID" --name="Citizens of India" 2>/dev/null || echo "Project already exists"
gcloud config set project "$PROJECT_ID"
echo "⚠️  Make sure billing is enabled: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
read -rp "Press Enter once billing is enabled..."

# ── Enable APIs ────────────────────────────────────────────────────────────────
echo "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  firestore.googleapis.com \
  speech.googleapis.com \
  translate.googleapis.com \
  bigquery.googleapis.com \
  aiplatform.googleapis.com \
  secretmanager.googleapis.com \
  firebase.googleapis.com \
  --project "$PROJECT_ID"

# ── Firestore ──────────────────────────────────────────────────────────────────
echo "Creating Firestore database..."
gcloud firestore databases create --location="$REGION" --project "$PROJECT_ID" 2>/dev/null || echo "Firestore already exists"

# ── BigQuery dataset ───────────────────────────────────────────────────────────
echo "Creating BigQuery dataset..."
bq mk --dataset --location=asia-south1 "$PROJECT_ID:constituency_data" 2>/dev/null || echo "Dataset already exists"

# ── Secrets ────────────────────────────────────────────────────────────────────
if [[ -n "$GEMINI_KEY" ]]; then
  echo "Storing Gemini API key in Secret Manager..."
  echo -n "$GEMINI_KEY" | gcloud secrets create gemini-api-key \
    --data-file=- --project "$PROJECT_ID" 2>/dev/null || \
    echo -n "$GEMINI_KEY" | gcloud secrets versions add gemini-api-key \
    --data-file=- --project "$PROJECT_ID"
fi

# ── Service account ────────────────────────────────────────────────────────────
SA_NAME="citizens-india-backend"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
echo "Creating service account..."
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="Citizens India Backend" \
  --project "$PROJECT_ID" 2>/dev/null || echo "SA already exists"

for ROLE in \
  roles/datastore.user \
  roles/bigquery.dataViewer \
  roles/bigquery.jobUser \
  roles/secretmanager.secretAccessor \
  roles/speech.client \
  roles/cloudtranslate.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" --role="$ROLE" --quiet
done

# ── Firebase init (manual step) ────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅  GCP setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run Firebase init:   firebase init hosting --project $PROJECT_ID"
echo "  2. Deploy backend:      gcloud builds submit --config deploy/cloudbuild.yaml"
echo "  3. Seed demo data:      python data/seed.py"
echo ""
echo "Cloud Run URL will be:"
echo "  https://citizens-india-backend-<hash>-$REGION.a.run.app"
echo "════════════════════════════════════════════════════════════"

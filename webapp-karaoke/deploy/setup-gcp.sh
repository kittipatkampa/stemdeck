#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:=us-central1}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com

if ! gcloud artifacts repositories describe karaoke --location="$REGION" >/dev/null 2>&1; then
  gcloud artifacts repositories create karaoke \
    --repository-format=docker \
    --location="$REGION" \
    --description="Karaoke web app images"
fi

for service in karaoke-api karaoke-web; do
  if ! gcloud iam service-accounts describe "${service}@${PROJECT_ID}.iam.gserviceaccount.com" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$service" \
      --display-name="Karaoke ${service#karaoke-} Cloud Run"
  fi
done

BUCKET="${PROJECT_ID}-karaoke-output"
if ! gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1; then
  gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${BUCKET}"
fi
gsutil lifecycle set "$ROOT/deploy/gcs-lifecycle.json" "gs://${BUCKET}"

echo "Setup complete. Output bucket: gs://${BUCKET}"

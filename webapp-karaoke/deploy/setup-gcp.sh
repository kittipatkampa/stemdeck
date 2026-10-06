#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:=us-central1}"

gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com

gcloud artifacts repositories create karaoke \
  --repository-format=docker \
  --location="$REGION" \
  --description="Karaoke web app images" \
  2>/dev/null || true

BUCKET="${PROJECT_ID}-karaoke-output"
gsutil mb -l "$REGION" "gs://${BUCKET}" 2>/dev/null || true
gsutil lifecycle set deploy/gcs-lifecycle.json "gs://${BUCKET}" 2>/dev/null || true

echo "Setup complete. Output bucket: gs://${BUCKET}"

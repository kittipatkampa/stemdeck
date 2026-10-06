#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:=us-central1}"
: "${KARAOKE_MODAL_APP:=karaoke-maker-prod}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/karaoke/api:latest"
BUCKET="${GCS_OUTPUT_BUCKET:-${PROJECT_ID}-karaoke-output}"

gcloud builds submit "$ROOT" \
  --config="$ROOT/deploy/cloudbuild-backend.yaml" \
  --substitutions="_IMAGE=${IMAGE}"

gcloud run deploy karaoke-api \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --max-instances=3 \
  --concurrency=10 \
  --set-env-vars="PIPELINE=modal,KARAOKE_MODAL_APP=${KARAOKE_MODAL_APP},GCS_OUTPUT_BUCKET=${BUCKET},MAX_CONCURRENT_JOBS=2" \
  --set-secrets="MODAL_TOKEN_ID=modal-token-id:latest,MODAL_TOKEN_SECRET=modal-token-secret:latest"

gcloud run services describe karaoke-api --region="$REGION" --format='value(status.url)'

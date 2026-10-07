#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:=us-central1}"
: "${BACKEND_URL:?Set BACKEND_URL to the backend Cloud Run URL}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/karaoke/web:latest"

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  gcloud builds submit "$ROOT" \
    --config="$ROOT/deploy/cloudbuild-frontend.yaml" \
    --substitutions="_IMAGE=${IMAGE}" \
    --project="$PROJECT_ID"
fi

gcloud run deploy karaoke-web \
  --project="$PROJECT_ID" \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --max-instances=1 \
  --service-account="karaoke-web@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars="BACKEND_URL=${BACKEND_URL}"

gcloud run services describe karaoke-web --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)'

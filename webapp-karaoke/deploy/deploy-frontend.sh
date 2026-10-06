#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:=us-central1}"
: "${VITE_API_BASE:?Set VITE_API_BASE to the backend Cloud Run URL}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/karaoke/web:latest"

gcloud builds submit "$ROOT" \
  --config="$ROOT/deploy/cloudbuild-frontend.yaml" \
  --substitutions="_IMAGE=${IMAGE},_VITE_API_BASE=${VITE_API_BASE}"

gcloud run deploy karaoke-web \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --max-instances=3

gcloud run services describe karaoke-web --region="$REGION" --format='value(status.url)'

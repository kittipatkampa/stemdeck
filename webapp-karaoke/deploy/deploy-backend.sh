#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${REGION:=us-central1}"
: "${KARAOKE_MODAL_APP:=karaoke-maker-prod}"
: "${MODAL_LOCAL_DOWNLOAD:=0}"
: "${FRONTEND_ORIGIN:?Set FRONTEND_ORIGIN to the deployed web URL}"
: "${DOWNLOAD_REGION:=us-west1}"

if [[ "$MODAL_LOCAL_DOWNLOAD" != "0" ]]; then
  echo "Cloud Run deployment requires MODAL_LOCAL_DOWNLOAD=0; background download threads are not durable." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/karaoke/api:latest"
if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  gcloud builds submit "$ROOT" \
    --config="$ROOT/deploy/cloudbuild-backend.yaml" \
    --substitutions="_IMAGE=${IMAGE}" \
    --project="$PROJECT_ID"
fi

gcloud run deploy karaoke-api \
  --project="$PROJECT_ID" \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=2Gi \
  --timeout=900 \
  --cpu=1 \
  --max-instances=1 \
  --concurrency=10 \
  --service-account="karaoke-api@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars="PIPELINE=modal,MODAL_LOCAL_DOWNLOAD=0,KARAOKE_MODAL_APP=${KARAOKE_MODAL_APP},MAX_CONCURRENT_JOBS=1,GCS_UPLOAD_BUCKET=${PROJECT_ID}-karaoke-output,FRONTEND_ORIGIN=${FRONTEND_ORIGIN},ENABLE_YOUTUBE_URLS=1,GCP_PROJECT_ID=${PROJECT_ID},GCP_DOWNLOAD_REGION=${DOWNLOAD_REGION},GCP_DOWNLOAD_JOB_NAME=karaoke-youtube-download" \
  --set-secrets="MODAL_TOKEN_ID=modal-token-id:latest,MODAL_TOKEN_SECRET=modal-token-secret:latest,ACCESS_CODE=karaoke-access-code:latest"

gcloud run services describe karaoke-api --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)'

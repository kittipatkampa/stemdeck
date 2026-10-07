#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${COOKIE_FILE:?Set COOKIE_FILE to the dedicated Netscape cookies.txt file}"
: "${DOWNLOAD_REGION:=us-west1}"
: "${KARAOKE_MODAL_APP:=karaoke-maker-prod}"
: "${DOWNLOAD_IMAGE_TAG:=20261006-v2}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUCKET="${PROJECT_ID}-karaoke-output"
JOB="karaoke-youtube-download"
SECRET="karaoke-youtube-cookies"
ACCOUNT="karaoke-downloader@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="us-central1-docker.pkg.dev/${PROJECT_ID}/karaoke/youtube-downloader:${DOWNLOAD_IMAGE_TAG}"

if [[ ! -s "$COOKIE_FILE" ]]; then
  echo "COOKIE_FILE is missing or empty" >&2
  exit 1
fi
if ! head -1 "$COOKIE_FILE" | grep -q 'Netscape HTTP Cookie File'; then
  echo "COOKIE_FILE must be Netscape cookies.txt format" >&2
  exit 1
fi

if ! gcloud secrets describe "$SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud secrets create "$SECRET" --replication-policy=automatic --project="$PROJECT_ID" >/dev/null
  gcloud secrets versions add "$SECRET" --data-file="$COOKIE_FILE" --project="$PROJECT_ID" >/dev/null
fi

if ! gcloud iam service-accounts describe "$ACCOUNT" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create karaoke-downloader \
    --display-name="Karaoke YouTube download job" --project="$PROJECT_ID" >/dev/null
fi
for secret in "$SECRET" modal-token-id modal-token-secret; do
  gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:${ACCOUNT}" \
    --role=roles/secretmanager.secretAccessor \
    --project="$PROJECT_ID" >/dev/null
done
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${ACCOUNT}" --role=roles/storage.objectCreator \
  --project="$PROJECT_ID" >/dev/null

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  gcloud builds submit "$ROOT" \
    --config="$ROOT/deploy/cloudbuild-downloader.yaml" \
    --substitutions="_IMAGE=${IMAGE}" \
    --project="$PROJECT_ID"
fi

flags=(
  --project="$PROJECT_ID"
  --region="$DOWNLOAD_REGION"
  --image="$IMAGE"
  --service-account="$ACCOUNT"
  --tasks=1
  --parallelism=1
  --max-retries=0
  --task-timeout=1200s
  --cpu=2
  --memory=2Gi
  --set-env-vars="KARAOKE_MODAL_APP=${KARAOKE_MODAL_APP},GCS_UPLOAD_BUCKET=${BUCKET},YTDLP_COOKIE_FILE=/secrets/cookies.txt,MAX_DURATION_SEC=600"
  --set-secrets="/secrets/cookies.txt=${SECRET}:latest,MODAL_TOKEN_ID=modal-token-id:latest,MODAL_TOKEN_SECRET=modal-token-secret:latest"
)
if gcloud run jobs describe "$JOB" --project="$PROJECT_ID" --region="$DOWNLOAD_REGION" >/dev/null 2>&1; then
  gcloud run jobs update "$JOB" "${flags[@]}"
else
  gcloud run jobs create "$JOB" "${flags[@]}"
fi
gcloud run jobs add-iam-policy-binding "$JOB" \
  --region="$DOWNLOAD_REGION" --project="$PROJECT_ID" \
  --member="serviceAccount:karaoke-api@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role=roles/run.jobsExecutorWithOverrides >/dev/null
echo "Download job ready: ${JOB} (${DOWNLOAD_REGION})"

#!/usr/bin/env bash
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${FRONTEND_ORIGIN:?Set FRONTEND_ORIGIN to the deployed web URL}"

BUCKET="${PROJECT_ID}-karaoke-output"
ACCOUNT="serviceAccount:karaoke-api@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="${ACCOUNT}" --role=roles/storage.objectCreator --project="${PROJECT_ID}"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="${ACCOUNT}" --role=roles/storage.objectViewer --project="${PROJECT_ID}"

cors_file="$(mktemp)"
trap 'rm -f "$cors_file"' EXIT
FRONTEND_ORIGIN="$FRONTEND_ORIGIN" python3 - "$cors_file" <<'PY'
import json
import os
import sys

with open(sys.argv[1], "w") as out:
    json.dump([{
        "origin": [os.environ["FRONTEND_ORIGIN"]],
        "method": ["PUT"],
        "responseHeader": ["Content-Type"],
        "maxAgeSeconds": 3600,
    }], out)
PY
gsutil cors set "$cors_file" "gs://${BUCKET}"
echo "Upload bucket ready: gs://${BUCKET}"

# GCP deployment

Deploy order: **backend → frontend → update backend CORS**.

## Prerequisites

1. GCP project with billing enabled.
2. `gcloud` CLI authenticated: `gcloud auth login`
3. Set variables:

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
export KARAOKE_MODAL_APP=karaoke-maker-prod
```

4. Modal deployed: `make deploy-modal` (with `KARAOKE_MODAL_APP` set for prod).
5. Secret Manager entries:
   - `modal-token-id`, `modal-token-secret` (from Modal settings)
   - Optional: Modal `youtube-cookies` with `YTDLP_COOKIES_B64` (YouTube bot check on datacenter IPs)
   - Optional: Modal `gcp-upload` with `GCP_SERVICE_ACCOUNT_JSON` and env `GCS_OUTPUT_BUCKET` on `run_job`

`gcloud` is not installed on this machine; run the scripts below from a workstation with the GCP CLI after creating a project.

## One-time setup

```bash
./deploy/setup-gcp.sh
```

Creates Artifact Registry, GCS output bucket (1-day lifecycle), and service accounts.

## Backend (Cloud Run)

```bash
./deploy/deploy-backend.sh
```

Note the service URL (e.g. `https://karaoke-api-xxxxx-uc.a.run.app`).

## Frontend (Cloud Run + nginx)

```bash
export VITE_API_BASE=https://karaoke-api-xxxxx-uc.a.run.app
./deploy/deploy-frontend.sh
```

Note the frontend URL, then update backend:

```bash
gcloud run services update karaoke-api \
  --region="$REGION" \
  --update-env-vars="FRONTEND_ORIGIN=https://karaoke-web-xxxxx-uc.a.run.app"
```

## Hardening

- Cloud Run: `--max-instances=3`, `--concurrency=10`
- Set `MAX_CONCURRENT_JOBS=1` on the API
- Enable Modal workspace spend limits
- Optional: `ACCESS_TOKEN` env on API (not implemented in v1; add before public launch)

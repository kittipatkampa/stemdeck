# GCP deployment

Deploy order: **Modal → backend → frontend**. The frontend proxies `/api` to the backend, so the browser keeps one origin for the access cookie and video playback.

## Prerequisites

1. GCP project with billing enabled. Current project: `karaoke-machine-kk-20261006` (display name `karaoke-machine`).
2. `gcloud` CLI authenticated with `kittipat@gmail.com`.
3. Set variables:

```bash
export PROJECT_ID=karaoke-machine-kk-20261006
export REGION=us-central1
export KARAOKE_MODAL_APP=karaoke-maker-prod
export FRONTEND_ORIGIN=https://karaoke-web-omadfssjbq-uc.a.run.app
```

4. The dedicated Netscape-format YouTube cookie file has been stored as Modal secret `youtube-cookies` (`YTDLP_COOKIES_B64`), and `karaoke-maker-prod` is deployed with it. Keep the source file and secret values out of Git.
5. Secret Manager entries:
   - `modal-token-id`, `modal-token-secret` (from Modal settings)
   - `karaoke-access-code` (one shared family code; stored as a secure, HTTP-only cookie after entry)
   - Planned: Modal `gcp-upload` with `GCP_SERVICE_ACCOUNT_JSON` and env `GCS_OUTPUT_BUCKET` for direct GCS output

The three GCP secrets and dedicated `karaoke-api` and `karaoke-web` service accounts have been created. The API account has Secret Manager access only to those three secrets. The current local access code is in `webapp-karaoke/.data/access-code.txt` (ignored by Git).

## One-time setup

```bash
./deploy/setup-gcp.sh
```

Creates Artifact Registry, the two service accounts, and a private GCS bucket with a 1-day lifecycle. Configure the bucket for device uploads after the frontend URL is known:

```bash
bash ./deploy/configure-upload-bucket.sh
```

This grants the API service account object create/read access and allows the frontend origin to PUT to a resumable upload session. The current API reads finished files from the Modal Volume. The setup and upload configuration ran successfully on 2026-10-06.

## Backend (Cloud Run)

```bash
./deploy/deploy-backend.sh
```

The script uses `MODAL_LOCAL_DOWNLOAD=0`, sets `ENABLE_YOUTUBE_URLS=0`, and enables `GCS_UPLOAD_BUCKET`. Browser files go directly to GCS, then the API copies them into the Modal Volume in a request with a 900-second timeout. The backend reads completed MP4s from the Modal Volume. Do not set `GCS_OUTPUT_BUCKET` on Cloud Run until Modal uploads outputs to that bucket and signed URL generation has been verified.

Cloud Run points to `karaoke-maker-prod` (API revision `karaoke-api-00005-45z`). YouTube returns “The page needs to be reloaded” during metadata lookup from Modal, so the public UI offers file upload. To reuse a previously built image, set `SKIP_BUILD=1`.

Note the service URL (e.g. `https://karaoke-api-xxxxx-uc.a.run.app`).

## Frontend (Cloud Run + nginx)

```bash
export BACKEND_URL=https://karaoke-api-omadfssjbq-uc.a.run.app
./deploy/deploy-frontend.sh
```

The current frontend is `https://karaoke-web-omadfssjbq-uc.a.run.app` (revision `karaoke-web-00003-wzg`). Its `/api` proxy and access cookie work. A fresh file upload via this URL completed as production job `87ea3a17d655`; the test checked CORS preflight, direct PUT, status to `done`, and a 206 MP4 range response. No phone-specific UI test has been run yet.

## Hardening

- Cloud Run uses `--max-instances=1`, `MAX_CONCURRENT_JOBS=1`, and a family access code.
- Files are limited to 500 MB and 10 minutes; inputs in the GCS bucket are deleted after 1 day by lifecycle policy. Completed MP4s remain on the Modal Volume until its cleanup job removes them after about 24 hours.
- The Modal workspace spend limit is $5 in monthly charges after credits are exhausted. The Starter workspace also has $30 of included compute credits. The limit applies to the existing dev app as well; Modal notes that Volume storage charges can continue after workloads stop.
- Modal Dict jobs idle for 30 minutes no longer count as active; the backend marks them failed when queried. The dev Modal app has a cron to remove 24-hour-old records and Volume files. Stale handling passed unit tests; an eligible old cloud job has not yet been observed being removed.

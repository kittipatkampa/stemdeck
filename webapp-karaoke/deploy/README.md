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
```

4. A dedicated Netscape-format YouTube cookie file. Create the Modal `youtube-cookies` secret with its contents in `YTDLP_COOKIES_B64`, then deploy with `KARAOKE_MODAL_APP=karaoke-maker-prod MODAL_SECRETS=youtube-cookies make deploy-modal`.
5. Secret Manager entries:
   - `modal-token-id`, `modal-token-secret` (from Modal settings)
   - `karaoke-access-code` (one shared family code; stored as a secure, HTTP-only cookie after entry)
   - Planned: Modal `gcp-upload` with `GCP_SERVICE_ACCOUNT_JSON` and env `GCS_OUTPUT_BUCKET` for direct GCS output

The three GCP secrets and dedicated `karaoke-api` and `karaoke-web` service accounts have been created. The API account has Secret Manager access only to those three secrets. The current local access code is in `webapp-karaoke/.data/access-code.txt` (ignored by Git).

## One-time setup

```bash
./deploy/setup-gcp.sh
```

Creates Artifact Registry, the two service accounts, and a GCS output bucket with a 1-day lifecycle. The bucket is reserved for the later direct-upload path; the current API reads finished files from the Modal Volume. This setup ran successfully on 2026-10-06.

## Backend (Cloud Run)

```bash
./deploy/deploy-backend.sh
```

The script uses `MODAL_LOCAL_DOWNLOAD=0`, so all work happens in Modal and Cloud Run does not rely on a background thread. It sets the family access code from Secret Manager. The backend reads completed MP4s from the Modal Volume. Do not set `GCS_OUTPUT_BUCKET` on Cloud Run until Modal uploads to that bucket and signed URL generation has been verified.

Cloud Run currently points to `karaoke-maker-dev` for a staging check against an existing completed job. Switch `KARAOKE_MODAL_APP` to `karaoke-maker-prod` only after deploying that Modal app with the YouTube cookies secret and verifying a new cloud job. To reuse a previously built image, set `SKIP_BUILD=1`.

Note the service URL (e.g. `https://karaoke-api-xxxxx-uc.a.run.app`).

## Frontend (Cloud Run + nginx)

```bash
export BACKEND_URL=https://karaoke-api-omadfssjbq-uc.a.run.app
./deploy/deploy-frontend.sh
```

The current frontend is `https://karaoke-web-omadfssjbq-uc.a.run.app`. Its `/api` proxy, access cookie, existing job status, and MP4 range response were verified against Cloud Run on 2026-10-06. New cloud downloads remain unverified until the dedicated cookie file is added to Modal.

## Hardening

- Cloud Run uses `--max-instances=1`, `MAX_CONCURRENT_JOBS=1`, and a family access code.
- The Modal workspace spend limit is $5 in monthly charges after credits are exhausted. The Starter workspace also has $30 of included compute credits. The limit applies to the existing dev app as well; Modal notes that Volume storage charges can continue after workloads stop.
- Modal Dict jobs idle for 30 minutes no longer count as active; the backend marks them failed when queried. The dev Modal app has a cron to remove 24-hour-old records and Volume files. Stale handling passed unit tests; an eligible old cloud job has not yet been observed being removed.

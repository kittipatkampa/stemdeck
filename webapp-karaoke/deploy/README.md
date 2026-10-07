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
5. The same dedicated cookie file is stored as GCP Secret Manager secret `karaoke-youtube-cookies` for the download job. It is mounted read-only, then copied to an owner-only temporary file before yt-dlp runs.
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

## YouTube downloader (Cloud Run Job)

```bash
export COOKIE_FILE=/absolute/path/to/dedicated-youtube-cookies.txt
bash ./deploy/deploy-youtube-downloader.sh
```

This builds the Deno/EJS/yt-dlp/FFmpeg image, creates a `karaoke-downloader` service account, grants it access to the three required secrets and GCS object creation, and deploys `karaoke-youtube-download` in `us-west1`. The API service account receives permission to run this job with URL and job-ID overrides. The job has one task, no automatic retries, a 20-minute timeout, a 500 MiB output limit, and a 10-minute video limit. The selected quality is at most 720p. The downloader uploads its source to private GCS, stages it in the Modal Volume, then spawns `run_uploaded_job`.

To rotate the GCP cookie secret after updating the dedicated file:

```bash
gcloud secrets versions add karaoke-youtube-cookies --data-file="$COOKIE_FILE" --project="$PROJECT_ID"
```

## Backend (Cloud Run)

```bash
./deploy/deploy-backend.sh
```

The script uses `MODAL_LOCAL_DOWNLOAD=0`, enables the GCP URL job and `GCS_UPLOAD_BUCKET`, and sets `ENABLE_YOUTUBE_URLS=1`. Browser files go directly to GCS, then the API copies them into the Modal Volume in a request with a 900-second timeout. URL requests start the Cloud Run Job without a long-lived API thread. The backend reads completed MP4s from the Modal Volume. Do not set `GCS_OUTPUT_BUCKET` on Cloud Run until Modal uploads outputs to that bucket and signed URL generation has been verified.

Cloud Run points to `karaoke-maker-prod` (API revision `karaoke-api-00006-lr9`). The public UI offers both URL and file panels. To reuse a previously built image, set `SKIP_BUILD=1`.

Note the service URL (e.g. `https://karaoke-api-xxxxx-uc.a.run.app`).

## Frontend (Cloud Run + nginx)

```bash
export BACKEND_URL=https://karaoke-api-omadfssjbq-uc.a.run.app
./deploy/deploy-frontend.sh
```

The current frontend is `https://karaoke-web-omadfssjbq-uc.a.run.app` (revision `karaoke-web-00004-vfg`). Its `/api` proxy and access cookie work. A fresh file upload completed as job `87ea3a17d655`. Fresh URL jobs `1f00211a9ef5` (short) and `69eea516931d` (three minutes) reached `done`, returned 206 MP4 range responses, and the full three-minute output had valid video/audio streams. No phone-specific UI test has been run yet.

## Hardening

- Cloud Run uses `--max-instances=1`, `MAX_CONCURRENT_JOBS=1`, and a family access code.
- Files are limited to 500 MB and 10 minutes; inputs in the GCS bucket are deleted after 1 day by lifecycle policy. Completed MP4s remain on the Modal Volume until its cleanup job removes them after about 24 hours.
- A GCP download can fail if YouTube changes its challenge or the dedicated cookie session expires. Keep the file upload route available.
- The Modal workspace spend limit is $5 in monthly charges after credits are exhausted. The Starter workspace also has $30 of included compute credits. The limit applies to the existing dev app as well; Modal notes that Volume storage charges can continue after workloads stop.
- Modal Dict jobs idle for 30 minutes no longer count as active; the backend marks them failed when queried. The dev Modal app has a cron to remove 24-hour-old records and Volume files. Stale handling passed unit tests; an eligible old cloud job has not yet been observed being removed.

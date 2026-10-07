# Karaoke web app

Turn a video into a vocal-free karaoke MP4. The public app accepts a YouTube URL or a video file from a laptop or phone. Frontend (Vite + React) talks to a thin FastAPI backend; a GCP job downloads YouTube videos, and [Modal](https://modal.com) runs vocal separation and video assembly.

## Prerequisites

- Python 3.11+, [uv](https://docs.astral.sh/uv/)
- Node.js 20+
- `ffmpeg` and `yt-dlp` on PATH (for local pipeline)
- Modal account (for `PIPELINE=modal` only)

## Local development (recommended)

```bash
cd webapp-karaoke/backend
uv sync --extra pipeline --group dev

cd ../frontend
npm install

cd ..
make dev
```

Open http://localhost:5173 and submit a YouTube URL. Default test Short:

`https://youtube.com/shorts/senFAeo0RQM`

Jobs and outputs are stored under `webapp-karaoke/.data/` (gitignored).

### Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE` | `local` | `local` (Mac CPU/MPS) or `modal` |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS origin |
| `KARAOKE_MODAL_APP` | `karaoke-maker-dev` | Modal app name |
| `MAX_CONCURRENT_JOBS` | `2` | Per-backend instance |
| `MAX_DURATION_SEC` | `600` | Max video length |
| `ACCESS_CODE` | unset | When set, require a shared code before API jobs and downloads |
| `GCS_UPLOAD_BUCKET` | unset | Enables browser-to-GCS video uploads in Modal mode |
| `ENABLE_YOUTUBE_URLS` | `1` | Public URL form also requires `GCP_DOWNLOAD_JOB_NAME` |
| `GCP_DOWNLOAD_JOB_NAME` | unset | Cloud Run Job used for YouTube downloads in production |
| `GCP_DOWNLOAD_REGION` | `us-west1` | Region of the download job |
| `GCP_PROJECT_ID` | unset | GCP project containing the download job |

## Modal (serverless GPU)

YouTube rejected metadata requests from the original Modal downloader. The public URL path now starts a Cloud Run Job in `us-west1` with yt-dlp, EJS, Deno, FFmpeg, and the dedicated YouTube cookies. It downloads to private GCS, stages the file in the Modal Volume, and starts `run_uploaded_job`. The browser file upload remains available. The public URL path completed fresh short and three-minute jobs on 2026-10-06; this verifies those inputs, not general YouTube reliability.

Deploy (attach secrets with `MODAL_SECRETS`):

```bash
KARAOKE_MODAL_APP=karaoke-maker-prod MODAL_SECRETS=youtube-cookies make deploy-modal
```

Run the API against Modal (default: download on your machine, GPU stem on Modal):

```bash
cd backend
PIPELINE=modal uv run uvicorn app.main:app --reload --port 8000
```

`MODAL_LOCAL_DOWNLOAD=0` delegates URL downloads to the configured GCP job in Cloud Run. Without `GCP_DOWNLOAD_JOB_NAME`, the API hides the URL form. The default local hybrid mode downloads on the API host, uploads extracted files to a Modal Volume, and runs the stem and mux steps there.

To repeat the live hybrid smoke test after deploying Modal, run `RUN_MODAL_SMOKE=1 make test`. Set `MODAL_SMOKE_JOB_ID=<completed ID>` to verify status and download for an existing job without starting another GPU run.

## Tests

```bash
make test
```

## Cloud staging

The staging frontend is [Dad's Karaoke](https://karaoke-web-omadfssjbq-uc.a.run.app). It uses a family access code and points to `karaoke-maker-prod`. A device-file upload completed as job `87ea3a17d655`. Fresh URL jobs `1f00211a9ef5` (short) and `69eea516931d` (three minutes) also completed through GCP download, private GCS, Modal, and MP4 download. The three-minute output was validated with FFprobe as 180.29 seconds of video and audio. See [deploy/README.md](deploy/README.md) for deployment details.

For multi-agent handoff (architecture, pitfalls, backlog), see **[docs/HANDOFF.md](docs/HANDOFF.md)**.

## Architecture

- `pipeline/` — shared download → extract → stem → combine stages
- `backend/` — FastAPI job API
- `modal/` — CPU orchestrator + GPU Demucs
- `frontend/` — React UI with `/j/:jobId` progress page

# Karaoke web app

Turn a video into a vocal-free karaoke MP4. The public app accepts a video file selected on a laptop or phone. Local development also accepts a YouTube URL. Frontend (Vite + React) talks to a thin FastAPI backend; heavy work runs locally (default) or on [Modal](https://modal.com) serverless GPU.

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
| `ENABLE_YOUTUBE_URLS` | `1` | Set to `0` on Cloud Run while YouTube rejects Modal metadata requests |

## Modal (serverless GPU)

YouTube has blocked downloads from the Modal cloud IP in testing. The dedicated YouTube account's Netscape-format `cookies.txt` is stored in the Modal `youtube-cookies` secret as `YTDLP_COOKIES_B64` (never in Git). The production Modal app uses that secret, but cloud metadata lookup still fails. The public app therefore accepts a file already saved on the user's device and uploads it directly to private GCS. The API stages it in the Modal Volume; the Modal CPU extracts tracks, the GPU separates vocals, and the CPU combines the MP4.

Deploy (attach secrets with `MODAL_SECRETS`):

```bash
KARAOKE_MODAL_APP=karaoke-maker-prod MODAL_SECRETS=youtube-cookies make deploy-modal
```

Run the API against Modal (default: download on your machine, GPU stem on Modal):

```bash
cd backend
PIPELINE=modal uv run uvicorn app.main:app --reload --port 8000
```

`MODAL_LOCAL_DOWNLOAD=0` makes Modal perform the full download; this is the current Cloud Run configuration but is blocked at YouTube. The default hybrid mode downloads on the API host, uploads extracted files to a Modal Volume, and runs the stem and mux steps there; this mode completed a fresh local-to-Modal job.

To repeat the live hybrid smoke test after deploying Modal, run `RUN_MODAL_SMOKE=1 make test`. Set `MODAL_SMOKE_JOB_ID=<completed ID>` to verify status and download for an existing job without starting another GPU run.

## Tests

```bash
make test
```

## Cloud staging

The staging frontend is [Dad's Karaoke](https://karaoke-web-omadfssjbq-uc.a.run.app). It uses a family access code and points to `karaoke-maker-prod`. A fresh 21 MB device-file upload completed as job `87ea3a17d655` on 2026-10-06, including browser CORS preflight, direct GCS PUT, Modal processing, and an MP4 range response. The user must first save the video file on the device; a web page cannot automatically download YouTube media from a pasted URL. See [deploy/README.md](deploy/README.md) for deployment details.

For multi-agent handoff (architecture, pitfalls, backlog), see **[docs/HANDOFF.md](docs/HANDOFF.md)**.

## Architecture

- `pipeline/` — shared download → extract → stem → combine stages
- `backend/` — FastAPI job API
- `modal/` — CPU orchestrator + GPU Demucs
- `frontend/` — React UI with `/j/:jobId` progress page

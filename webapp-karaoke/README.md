# Karaoke web app

Turn a YouTube URL into a vocal-free karaoke MP4. Frontend (Vite + React) talks to a thin FastAPI backend; heavy work runs locally (default) or on [Modal](https://modal.com) serverless GPU.

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

## Modal (serverless GPU)

YouTube has blocked downloads from the Modal cloud IP in testing. The dedicated YouTube account's Netscape-format `cookies.txt` is stored in the Modal `youtube-cookies` secret as `YTDLP_COOKIES_B64` (never in Git). The production Modal app uses that secret, but new cloud jobs still fail during YouTube metadata lookup with “The page needs to be reloaded.” The same cookies and yt-dlp version work from this Mac. A different download path is needed before sharing the cloud app for new jobs.

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

The staging frontend is [Dad's Karaoke](https://karaoke-web-omadfssjbq-uc.a.run.app). It uses a family access code and points to `karaoke-maker-prod`. An existing dev job returned status and an MP4 range through the Cloud Run proxy. Fresh production jobs reached Modal but failed at YouTube metadata lookup despite the dedicated cookie secret. See [deploy/README.md](deploy/README.md) for the project, scripts, and current blocker.

For multi-agent handoff (architecture, pitfalls, backlog), see **[docs/HANDOFF.md](docs/HANDOFF.md)**.

## Architecture

- `pipeline/` — shared download → extract → stem → combine stages
- `backend/` — FastAPI job API
- `modal/` — CPU orchestrator + GPU Demucs
- `frontend/` — React UI with `/j/:jobId` progress page

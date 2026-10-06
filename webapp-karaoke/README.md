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

YouTube has blocked downloads from the Modal cloud IP in testing. Cloud-hosted downloads need a dedicated YouTube account's Netscape-format `cookies.txt`; keep it out of Git. Encode its contents as `YTDLP_COOKIES_B64` in the Modal `youtube-cookies` secret, then attach that secret when deploying the Modal app. The dedicated cookie file and a fresh cloud job are still pending.

Deploy (attach secrets with `MODAL_SECRETS`):

```bash
KARAOKE_MODAL_APP=karaoke-maker-prod MODAL_SECRETS=youtube-cookies make deploy-modal
```

Run the API against Modal (default: download on your machine, GPU stem on Modal):

```bash
cd backend
PIPELINE=modal uv run uvicorn app.main:app --reload --port 8000
```

Set `MODAL_LOCAL_DOWNLOAD=0` only when Modal can download YouTube, typically with the `youtube-cookies` secret. The default hybrid mode downloads on the API host, uploads extracted files to a Modal Volume, and runs the stem and mux steps there.

To repeat the live hybrid smoke test after deploying Modal, run `RUN_MODAL_SMOKE=1 make test`. Set `MODAL_SMOKE_JOB_ID=<completed ID>` to verify status and download for an existing job without starting another GPU run.

## Tests

```bash
make test
```

## Cloud staging

The staging frontend is [Dad's Karaoke](https://karaoke-web-omadfssjbq-uc.a.run.app). It uses a family access code and currently points to the dev Modal app. An existing completed job returned status and an MP4 range through the Cloud Run proxy; no fresh Cloud Run job has completed yet. The dedicated YouTube cookie file is the remaining dependency for that test. See [deploy/README.md](deploy/README.md) for the project, scripts, and verification steps.

For multi-agent handoff (architecture, pitfalls, backlog), see **[docs/HANDOFF.md](docs/HANDOFF.md)**.

## Architecture

- `pipeline/` — shared download → extract → stem → combine stages
- `backend/` — FastAPI job API
- `modal/` — CPU orchestrator + GPU Demucs
- `frontend/` — React UI with `/j/:jobId` progress page

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

## Modal (serverless GPU)

YouTube often blocks datacenter IPs. A Phase 0 spike on Modal failed with “Sign in to confirm you're not a bot”. For Modal downloads, provide cookies:

```bash
modal secret create youtube-cookies \
  YTDLP_COOKIES_B64="$(base64 < /path/to/cookies.txt | tr -d '\n')"
```

Deploy (attach secrets with `MODAL_SECRETS`):

```bash
MODAL_SECRETS=youtube-cookies make deploy-modal
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

## GCP deploy (Phase 3)

See [deploy/README.md](deploy/README.md). Requires `gcloud`, a GCP project with billing, and Modal tokens in Secret Manager.

For multi-agent handoff (architecture, pitfalls, backlog), see **[docs/HANDOFF.md](docs/HANDOFF.md)**.

## Architecture

- `pipeline/` — shared download → extract → stem → combine stages
- `backend/` — FastAPI job API
- `modal/` — CPU orchestrator + GPU Demucs
- `frontend/` — React UI with `/j/:jobId` progress page

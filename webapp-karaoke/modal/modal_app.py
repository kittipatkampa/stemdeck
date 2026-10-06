"""Modal app: CPU orchestration + GPU stem separation for karaoke jobs."""

from __future__ import annotations

import base64
import os
import shutil
import tempfile
import time
from pathlib import Path

import modal

APP_NAME = os.environ.get("KARAOKE_MODAL_APP", "karaoke-maker-dev")
DICT_NAME = f"{APP_NAME}-jobs"
VOLUME_NAME = f"{APP_NAME}-work"

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
jobs_state = modal.Dict.from_name(DICT_NAME, create_if_missing=True)

DATA_ROOT = Path("/data/karaoke")


def _modal_secrets() -> list[modal.Secret]:
    names = os.environ.get("MODAL_SECRETS", "")
    return [modal.Secret.from_name(n.strip()) for n in names.split(",") if n.strip()]


_PIPELINE_DIR = Path(__file__).resolve().parent.parent / "pipeline"


def _preload_demucs_weights() -> None:
    from demucs.pretrained import get_model

    get_model("htdemucs")


cpu_image = (
    modal.Image.from_registry("debian:bookworm-slim", add_python="3.11")
    .apt_install("ffmpeg")
    .pip_install("yt-dlp>=2026.7.4", "google-cloud-storage>=2.18")
    .add_local_dir(_PIPELINE_DIR, remote_path="/root/pipeline", copy=True)
)

gpu_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch==2.6.0",
        "torchaudio==2.6.0",
        "demucs>=4.0.1,<4.1",
        "soundfile>=0.12.1",
    )
    .run_function(_preload_demucs_weights, gpu="T4")
    .add_local_dir(_PIPELINE_DIR, remote_path="/root/pipeline", copy=True)
)


def _cookiefile_from_env() -> str | None:
    raw = os.environ.get("YTDLP_COOKIES_B64")
    if not raw:
        return None
    path = Path(tempfile.gettempdir()) / "youtube_cookies.txt"
    path.write_bytes(base64.b64decode(raw))
    return str(path)


def _upload_to_gcs_if_configured(job_id: str, path: Path) -> None:
    bucket = os.environ.get("GCS_OUTPUT_BUCKET")
    if not bucket or not path.is_file():
        return
    from google.cloud import storage
    from google.oauth2 import service_account
    import json

    raw = os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
    if raw:
        creds = service_account.Credentials.from_service_account_info(json.loads(raw))
        client = storage.Client(credentials=creds, project=creds.project_id)
    else:
        client = storage.Client()
    blob = client.bucket(bucket).blob(f"jobs/{job_id}.mp4")
    blob.upload_from_filename(str(path), content_type="video/mp4")


def _update_job(job_id: str, **fields) -> None:
    current = jobs_state.get(job_id) or {}
    jobs_state[job_id] = {**current, **fields}


def _finish_stem_and_mux(job_id: str, model: str, report) -> None:
    """Stem on GPU, mux on CPU; expects job_dir/audio.wav and video_only.mp4."""
    from pipeline.progress import overall_progress
    from pipeline.stages import mux_karaoke, require_ffmpeg

    job_dir = DATA_ROOT / "jobs" / job_id
    output_mp4 = job_dir / "output.mp4"
    video_only = job_dir / "video_only.mp4"
    if not video_only.is_file():
        raise FileNotFoundError(f"missing video_only.mp4 for job {job_id}")

    _update_job(job_id, stage="stem", stage_progress=0.0)
    separate_stems.remote(job_id, model)
    volume.reload()
    _update_job(
        job_id,
        stage="stem",
        stage_progress=1.0,
        overall_progress=overall_progress("stem", 1.0),
    )

    ffmpeg = require_ffmpeg()
    no_vocals = job_dir / "no_vocals.wav"
    if not no_vocals.is_file():
        raise FileNotFoundError(f"missing no_vocals.wav for job {job_id}")
    mux_karaoke(ffmpeg, video_only, no_vocals, output_mp4, report)
    volume.commit()
    _upload_to_gcs_if_configured(job_id, output_mp4)


@app.function(
    image=cpu_image,
    timeout=900,
    volumes={"/data": volume},
    secrets=_modal_secrets(),
)
def run_staged_job(
    job_id: str,
    model: str = "htdemucs",
) -> None:
    """Continue a job after the API host uploads extracted files to the Volume."""
    import sys

    sys.path.insert(0, "/root")
    from pipeline.errors import PipelineError
    from pipeline.progress import Stage, overall_progress

    def report(stage: Stage, pct: float, extra: dict) -> None:
        _update_job(
            job_id,
            status="running",
            stage=stage,
            stage_progress=pct,
            overall_progress=extra.get("overall_progress", overall_progress(stage, pct)),
            error=None,
        )

    try:
        job_dir = DATA_ROOT / "jobs" / job_id
        volume.reload()
        if not (job_dir / "audio.wav").is_file():
            raise FileNotFoundError(f"missing audio.wav for job {job_id}")
        if not (job_dir / "video_only.mp4").is_file():
            raise FileNotFoundError(f"missing video_only.mp4 for job {job_id}")
        _finish_stem_and_mux(job_id, model, report)
        _update_job(
            job_id,
            status="done",
            stage="combine",
            stage_progress=1.0,
            overall_progress=1.0,
        )
    except PipelineError as e:
        _update_job(job_id, status="failed", error=str(e))
    except Exception as e:
        _update_job(job_id, status="failed", error=str(e))


@app.function(
    image=gpu_image,
    gpu="T4",
    timeout=900,
    volumes={"/data": volume},
    scaledown_window=10,
    max_containers=4,
)
def separate_stems(job_id: str, model: str = "htdemucs") -> str:
    import sys

    sys.path.insert(0, "/root")
    from pipeline.stages import separate_vocals

    volume.reload()
    job_dir = DATA_ROOT / "jobs" / job_id
    audio = job_dir / "audio.wav"
    if not audio.is_file():
        raise FileNotFoundError(f"missing audio for job {job_id}")
    out_dir = job_dir / "stems"
    no_vocals = separate_vocals(audio, out_dir, model, "cuda", report=None)
    dest = job_dir / "no_vocals.wav"
    shutil.copy2(no_vocals, dest)
    volume.commit()
    return str(dest)


@app.function(
    image=cpu_image,
    timeout=1200,
    volumes={"/data": volume},
    secrets=_modal_secrets(),
)
def run_job(job_id: str, youtube_url: str, model: str = "htdemucs") -> None:
    import sys

    sys.path.insert(0, "/root")
    from pipeline.errors import PipelineError
    from pipeline.progress import Stage, overall_progress
    from pipeline.stages import download_video, extract_tracks, require_ffmpeg

    job_dir = DATA_ROOT / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    output_mp4 = job_dir / "output.mp4"
    cookiefile = _cookiefile_from_env()

    def report(stage: Stage, pct: float, extra: dict) -> None:
        title = extra.get("title")
        payload = {
            "status": "running",
            "stage": stage,
            "stage_progress": pct,
            "overall_progress": extra.get("overall_progress", overall_progress(stage, pct)),
            "error": None,
        }
        if title:
            payload["title"] = title
        _update_job(job_id, **payload)

    _update_job(
        job_id,
        status="running",
        stage="download",
        stage_progress=0.0,
        overall_progress=0.0,
        error=None,
    )

    try:
        ffmpeg = require_ffmpeg()
        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            tmp_path = Path(tmp)
            video_path, title, _vid = download_video(
                youtube_url,
                tmp_path / "dl",
                ffmpeg,
                report,
                cookiefile,
            )
            _update_job(job_id, title=title)
            video_only, audio_wav = extract_tracks(ffmpeg, video_path, tmp_path / "extract", report)
            shutil.copy2(audio_wav, job_dir / "audio.wav")
            shutil.copy2(video_only, job_dir / "video_only.mp4")
            volume.commit()

            _finish_stem_and_mux(job_id, model, report)

        _update_job(
            job_id,
            status="done",
            stage="combine",
            stage_progress=1.0,
            overall_progress=1.0,
            output_path=str(output_mp4),
        )
    except PipelineError as e:
        _update_job(job_id, status="failed", error=str(e))
    except Exception as e:
        _update_job(job_id, status="failed", error=str(e))


@app.function(image=cpu_image, schedule=modal.Cron("0 */6 * * *"), volumes={"/data": volume})
def cleanup_old_jobs(max_age_hours: int = 24) -> int:
    if not DATA_ROOT.exists():
        return 0
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    jobs_root = DATA_ROOT / "jobs"
    if not jobs_root.exists():
        return 0
    for child in jobs_root.iterdir():
        if not child.is_dir():
            continue
        if child.stat().st_mtime < cutoff:
            shutil.rmtree(child, ignore_errors=True)
            jobs_state.pop(child.name, None)
            removed += 1
    volume.commit()
    return removed

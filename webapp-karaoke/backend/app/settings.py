from __future__ import annotations

import os
from pathlib import Path

WEBAPP_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = WEBAPP_ROOT / "pipeline"
DATA_DIR = WEBAPP_ROOT / ".data"


def get_pipeline_mode() -> str:
    return os.environ.get("PIPELINE", "local").lower()


def get_frontend_origin() -> str:
    return os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")


def get_modal_app_name() -> str:
    return os.environ.get("KARAOKE_MODAL_APP", "karaoke-maker-dev")


def get_max_concurrent_jobs() -> int:
    return int(os.environ.get("MAX_CONCURRENT_JOBS", "2"))


def get_max_duration_sec() -> int:
    return int(os.environ.get("MAX_DURATION_SEC", "600"))


def get_gcs_bucket() -> str | None:
    return os.environ.get("GCS_OUTPUT_BUCKET")


def get_storage_mode() -> str:
    if get_gcs_bucket():
        return "gcs"
    return "local"


def modal_local_download() -> bool:
    """Download on the API host, then stem on Modal (avoids YouTube bot checks on Modal IPs)."""
    return os.environ.get("MODAL_LOCAL_DOWNLOAD", "1").lower() in ("1", "true", "yes")


def ytdlp_cookie_file() -> str | None:
    path = os.environ.get("YTDLP_COOKIE_FILE")
    if path and Path(path).is_file():
        return path
    return None

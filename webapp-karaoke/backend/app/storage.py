from __future__ import annotations

from pathlib import Path
from typing import Iterator

import modal

from app.job_state import output_path
from app.settings import DATA_DIR, get_gcs_bucket, get_modal_app_name, get_storage_mode


class JobNotReadyError(FileNotFoundError):
    pass


def local_output(job_id: str) -> Path:
    path = output_path(job_id)
    if path.is_file():
        return path
    raise JobNotReadyError(job_id)


def _modal_volume_path(job_id: str) -> str:
    return f"karaoke/jobs/{job_id}/output.mp4"


def fetch_modal_output(job_id: str, dest: Path) -> Path:
    vol = modal.Volume.from_name(f"{get_modal_app_name()}-work", create_if_missing=True)
    remote = _modal_volume_path(job_id)
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.with_suffix(".download")
    try:
        with temp.open("wb") as out:
            for chunk in vol.read_file(remote):
                out.write(chunk)
        if temp.stat().st_size == 0:
            raise JobNotReadyError(job_id)
        temp.replace(dest)
    except Exception as e:
        temp.unlink(missing_ok=True)
        raise JobNotReadyError(job_id) from e
    return dest


def resolve_output_path(job_id: str) -> Path:
    try:
        return local_output(job_id)
    except JobNotReadyError:
        cache = DATA_DIR / "jobs" / job_id / "output.mp4"
        if cache.is_file():
            return cache
        return fetch_modal_output(job_id, cache)


def stream_file(path: Path, chunk_size: int = 1024 * 1024) -> Iterator[bytes]:
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


def gcs_signed_url(job_id: str, expires_seconds: int = 600) -> str | None:
    bucket_name = get_gcs_bucket()
    if not bucket_name or get_storage_mode() != "gcs":
        return None
    from google.cloud import storage
    from datetime import timedelta

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"jobs/{job_id}.mp4")
    if not blob.exists():
        return None
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=expires_seconds),
        method="GET",
    )

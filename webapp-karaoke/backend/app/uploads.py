"""Private browser-to-GCS uploads for video files selected on a device."""

from __future__ import annotations

from pathlib import Path

from google.cloud import storage

from app.settings import get_frontend_origin

MAX_UPLOAD_BYTES = 500 * 1024 * 1024
VIDEO_TYPES = {
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
}


def video_details(filename: str, size: int) -> tuple[str, str]:
    name = Path(filename).name[:120]
    suffix = Path(name).suffix.lower()
    if suffix not in VIDEO_TYPES:
        raise ValueError("Choose an MP4, MOV, WebM, MKV, or M4V video")
    if size <= 0 or size > MAX_UPLOAD_BYTES:
        raise ValueError("Video must be between 1 byte and 500 MB")
    return name, VIDEO_TYPES[suffix]


def upload_blob(bucket_name: str, job_id: str, client: storage.Client | None = None):
    client = client or storage.Client()
    return client.bucket(bucket_name).blob(f"uploads/{job_id}/source")


def create_upload_session(bucket_name: str, job_id: str, filename: str, size: int) -> str:
    name, content_type = video_details(filename, size)
    blob = upload_blob(bucket_name, job_id)
    blob.metadata = {"source_name": name}
    return blob.create_resumable_upload_session(
        content_type=content_type,
        size=size,
        origin=get_frontend_origin(),
        if_generation_match=0,
    )


def download_verified_upload(bucket_name: str, job_id: str, expected_size: int, dest: Path) -> str:
    blob = upload_blob(bucket_name, job_id)
    if not blob.exists():
        raise ValueError("Upload has not finished")
    blob.reload()
    if blob.size != expected_size or not blob.size or blob.size > MAX_UPLOAD_BYTES:
        raise ValueError("Uploaded file size does not match")
    name = (blob.metadata or {}).get("source_name", "video.mp4")
    video_details(name, blob.size)
    dest.parent.mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(str(dest))
    if dest.stat().st_size != expected_size:
        raise ValueError("Uploaded file is incomplete")
    return name

"""Cloud Run Job: download one YouTube video to private GCS, then start Modal processing."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import modal
from google.cloud import storage

from pipeline.urls import validate_youtube_url

MAX_BYTES = 500 * 1024 * 1024
ALLOWED_SUFFIXES = {".mp4", ".mkv", ".webm"}


def _set_state(jobs: modal.Dict, job_id: str, **fields: object) -> None:
    current = jobs.get(job_id) or {}
    jobs[job_id] = {**current, **fields, "updated_at": time.time()}


def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        diagnostics = [line for line in result.stderr.splitlines() if "ERROR:" in line]
        detail = diagnostics[-1] if diagnostics else result.stderr.strip().splitlines()[-1] if result.stderr.strip() else f"yt-dlp exited {result.returncode}"
        detail = re.sub(r"https?://\S+", "[URL]", detail)
        detail = re.sub(r"(?i)(cookie|authorization|po_token)([=: ]+)\S+", r"\1\2[REDACTED]", detail)
        raise RuntimeError(detail[:400])
    return result


def _probe_video(path: Path, max_duration: int) -> None:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    data = json.loads(result.stdout)
    streams = {stream.get("codec_type") for stream in data.get("streams", [])}
    duration = float(data.get("format", {}).get("duration") or 0)
    if not {"video", "audio"} <= streams:
        raise ValueError("Downloaded file needs video and audio")
    if duration <= 0 or duration > max_duration + 2:
        raise ValueError(f"Video must be at most {max_duration // 60} minutes")
    if path.stat().st_size <= 0 or path.stat().st_size > MAX_BYTES:
        raise ValueError("Downloaded video exceeds the 500 MB limit")


def main() -> None:
    job_id = os.environ["KARAOKE_JOB_ID"]
    if not re.fullmatch(r"[0-9a-f]{12}", job_id):
        raise ValueError("Invalid job ID")
    url = validate_youtube_url(os.environ["YOUTUBE_URL"])
    bucket_name = os.environ["GCS_UPLOAD_BUCKET"]
    app_name = os.environ["KARAOKE_MODAL_APP"]
    max_duration = int(os.environ.get("MAX_DURATION_SEC", "600"))
    cookie_file = Path(os.environ["YTDLP_COOKIE_FILE"])
    if not cookie_file.is_file():
        raise FileNotFoundError("YouTube cookie secret is missing")
    jobs = modal.Dict.from_name(f"{app_name}-jobs", create_if_missing=True)
    if jobs.get(job_id) is None:
        raise ValueError("Job was not created by the API")

    try:
        with tempfile.TemporaryDirectory(prefix="karaoke-youtube-") as temp_dir:
            work = Path(temp_dir)
            writable_cookies = work / "cookies.txt"
            shutil.copyfile(cookie_file, writable_cookies)
            writable_cookies.chmod(0o600)
            common = [
                sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-plugin-dirs",
                "--js-runtimes", "deno", "--no-playlist", "--cookies", str(writable_cookies),
                "--socket-timeout", "30", "--retries", "2", "--extractor-retries", "2",
                "--fragment-retries", "2", "--no-progress", "--max-filesize", "500M",
                "--match-filter", f"duration <= {max_duration} & !is_live",
                "-f", "bv*[height<=720]+ba/b[height<=720]", "--merge-output-format", "mp4",
                "-o", str(work / "media.%(ext)s"),
            ]
            _set_state(jobs, job_id, status="running", stage="download", stage_progress=0.05)
            metadata = json.loads(_run(common + ["--skip-download", "--dump-single-json", url], 180).stdout)
            duration = metadata.get("duration")
            if not duration or float(duration) > max_duration or metadata.get("is_live"):
                raise ValueError(f"Video must be at most {max_duration // 60} minutes and not live")
            title = str(metadata.get("title") or metadata.get("id") or "YouTube video")[:160]
            _set_state(jobs, job_id, title=title, stage_progress=0.15)
            _run(common + [url], 900)
            candidates = [path for path in work.iterdir() if path.suffix in ALLOWED_SUFFIXES]
            if not candidates:
                raise FileNotFoundError("YouTube download produced no video")
            source = max(candidates, key=lambda path: path.stat().st_size)
            _probe_video(source, max_duration)
            _set_state(jobs, job_id, stage_progress=0.8)

            blob = storage.Client().bucket(bucket_name).blob(f"uploads/{job_id}/source")
            blob.metadata = {"source_name": f"{metadata.get('id') or job_id}{source.suffix}"}
            blob.upload_from_filename(
                str(source), content_type="video/mp4" if source.suffix == ".mp4" else "application/octet-stream",
                if_generation_match=0, timeout=600,
            )
            volume = modal.Volume.from_name(f"{app_name}-work", create_if_missing=True)
            with volume.batch_upload() as batch:
                batch.put_file(str(source), f"karaoke/jobs/{job_id}/source{source.suffix}")
            _set_state(jobs, job_id, status="queued", stage_progress=1.0, overall_progress=0.2)
            modal.Function.from_name(app_name, "run_uploaded_job").spawn(
                job_id, source.suffix, max_duration
            )
            print(json.dumps({"job_id": job_id, "status": "processing", "bytes": source.stat().st_size}))
    except Exception as error:
        _set_state(jobs, job_id, status="failed", error=str(error)[:400])
        raise


if __name__ == "__main__":
    main()

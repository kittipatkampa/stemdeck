"""Start a bounded Cloud Run Job for a YouTube URL."""

from __future__ import annotations

import os

import google.auth
from google.auth.transport.requests import AuthorizedSession


def download_job_name() -> str | None:
    return os.environ.get("GCP_DOWNLOAD_JOB_NAME")


def start_download(job_id: str, url: str) -> None:
    job_name = download_job_name()
    if not job_name:
        raise RuntimeError("GCP download job is not configured")
    project = os.environ["GCP_PROJECT_ID"]
    region = os.environ.get("GCP_DOWNLOAD_REGION", "us-west1")
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    session = AuthorizedSession(credentials)
    response = session.post(
        f"https://run.googleapis.com/v2/projects/{project}/locations/{region}/jobs/{job_name}:run",
        json={"overrides": {"containerOverrides": [{"env": [
            {"name": "KARAOKE_JOB_ID", "value": job_id},
            {"name": "YOUTUBE_URL", "value": url},
        ]}]}},
        timeout=30,
    )
    response.raise_for_status()

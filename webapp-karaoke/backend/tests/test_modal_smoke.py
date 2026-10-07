"""Opt-in live Modal hybrid smoke test. Uses an existing job when supplied."""

import os
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import runner


@pytest.mark.skipif(
    os.environ.get("RUN_MODAL_SMOKE") != "1",
    reason="Set RUN_MODAL_SMOKE=1 for a live Modal hybrid test",
)
def test_modal_hybrid_job(monkeypatch):
    monkeypatch.setenv("PIPELINE", "modal")
    monkeypatch.setenv("MODAL_LOCAL_DOWNLOAD", "1")
    runner._runner = None
    try:
        client = TestClient(app)
        job_id = os.environ.get("MODAL_SMOKE_JOB_ID")
        if not job_id:
            response = client.post(
                "/api/jobs",
                json={"url": "https://youtube.com/shorts/senFAeo0RQM"},
            )
            assert response.status_code == 202, response.text
            job_id = response.json()["job_id"]

        deadline = time.monotonic() + 180
        while True:
            response = client.get(f"/api/jobs/{job_id}")
            assert response.status_code == 200, response.text
            state = response.json()
            if state["status"] in ("done", "failed"):
                break
            assert time.monotonic() < deadline, state
            time.sleep(2)

        assert state["status"] == "done", state
        response = client.get(f"/api/jobs/{job_id}/download")
        assert response.status_code == 200, response.text[:500]
        assert response.headers["content-type"].startswith("video/mp4")
        assert len(response.content) > 100_000
        assert b"ftyp" in response.content[:64]
    finally:
        runner._runner = None

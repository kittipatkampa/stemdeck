import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert client.get("/api/healthz").status_code == 200


def test_create_job_rejects_bad_url():
    r = client.post("/api/jobs", json={"url": "https://not-youtube.com/x"})
    assert r.status_code == 400


def test_create_job_accepts_shorts():
    r = client.post("/api/jobs", json={"url": "https://youtube.com/shorts/senFAeo0RQM"})
    assert r.status_code == 202
    body = r.json()
    assert "job_id" in body

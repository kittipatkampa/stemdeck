from fastapi.testclient import TestClient

from app import main
from app.settings import youtube_urls_enabled


def test_cloud_url_option_requires_download_job(monkeypatch):
    monkeypatch.setenv("PIPELINE", "modal")
    monkeypatch.setenv("MODAL_LOCAL_DOWNLOAD", "0")
    monkeypatch.setenv("ENABLE_YOUTUBE_URLS", "1")
    monkeypatch.delenv("GCP_DOWNLOAD_JOB_NAME", raising=False)
    assert not youtube_urls_enabled()
    monkeypatch.setenv("GCP_DOWNLOAD_JOB_NAME", "karaoke-youtube-download")
    assert youtube_urls_enabled()


def test_url_job_dispatches_to_gcp_with_canonical_url(monkeypatch):
    monkeypatch.delenv("ACCESS_CODE", raising=False)
    monkeypatch.setenv("PIPELINE", "modal")
    monkeypatch.setenv("MODAL_LOCAL_DOWNLOAD", "0")
    monkeypatch.setenv("ENABLE_YOUTUBE_URLS", "1")
    monkeypatch.setenv("GCP_DOWNLOAD_JOB_NAME", "karaoke-youtube-download")
    monkeypatch.setattr(main, "active_job_count", lambda: 0)
    dispatched = []

    class FakeRunner:
        def reserve_gcp_download(self, job_id):
            dispatched.append(("reserve", job_id))

        def fail_upload(self, job_id, error):
            raise AssertionError(error)

        def start(self, job_id, url):
            raise AssertionError("Modal downloader should not run")

    runner = FakeRunner()
    monkeypatch.setattr(main, "ModalRunner", FakeRunner)
    monkeypatch.setattr(main, "get_runner", lambda: runner)
    monkeypatch.setattr(main, "start_download", lambda job_id, url: dispatched.append((job_id, url)))

    response = TestClient(main.app).post(
        "/api/jobs", json={"url": "https://youtu.be/SgDqxwZdjmw?t=30"}
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert dispatched == [
        ("reserve", job_id),
        (job_id, "https://www.youtube.com/watch?v=SgDqxwZdjmw"),
    ]

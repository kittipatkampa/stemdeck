from fastapi.testclient import TestClient

from app.main import app


def test_access_code_protects_jobs_and_media(monkeypatch):
    monkeypatch.setenv("ACCESS_CODE", "test-code")
    client = TestClient(app)

    assert client.get("/healthz").status_code == 200
    assert client.get("/api/access").json() == {
        "required": True,
        "authorized": False,
    }
    assert client.post("/api/jobs", json={"url": "https://youtube.com/shorts/senFAeo0RQM"}).status_code == 401
    assert client.get("/api/jobs/example").status_code == 401
    assert client.get("/api/jobs/example/download").status_code == 401

    assert client.post("/api/access", json={"code": "wrong"}).status_code == 401
    unlocked = client.post("/api/access", json={"code": "test-code"})
    assert unlocked.status_code == 200
    assert "httponly" in unlocked.headers["set-cookie"].lower()
    assert "samesite=lax" in unlocked.headers["set-cookie"].lower()
    assert client.get("/api/access").json()["authorized"] is True
    assert client.get("/api/jobs/example").status_code == 404

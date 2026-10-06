from app import runner


def test_stale_modal_jobs_do_not_block_new_jobs(monkeypatch):
    monkeypatch.setattr(runner.time, "time", lambda: 10_000)
    modal_runner = runner.ModalRunner.__new__(runner.ModalRunner)
    modal_runner._dict = {
        "old": {"status": "running", "updated_at": 8_000},
        "legacy": {"status": "running"},
        "current": {"status": "running", "updated_at": 9_990},
    }

    assert modal_runner.count_active() == 1
    assert modal_runner.get("old")["status"] == "failed"
    assert modal_runner.get("old")["error"] == "Job timed out"
    assert modal_runner.get("legacy")["status"] == "failed"

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.settings import DATA_DIR

_lock = threading.Lock()


def _job_dir(job_id: str) -> Path:
    return DATA_DIR / "jobs" / job_id


def _state_path(job_id: str) -> Path:
    return _job_dir(job_id) / "state.json"


def init_job(job_id: str, url: str) -> dict[str, Any]:
    state = {
        "job_id": job_id,
        "url": url,
        "status": "queued",
        "stage": "download",
        "stage_progress": 0.0,
        "overall_progress": 0.0,
        "title": None,
        "error": None,
    }
    with _lock:
        _job_dir(job_id).mkdir(parents=True, exist_ok=True)
        _state_path(job_id).write_text(json.dumps(state), encoding="utf-8")
    return state


def update_job(job_id: str, **fields: Any) -> dict[str, Any]:
    with _lock:
        path = _state_path(job_id)
        if not path.is_file():
            raise KeyError(job_id)
        state = json.loads(path.read_text(encoding="utf-8"))
        state.update(fields)
        path.write_text(json.dumps(state), encoding="utf-8")
        return state


def get_job(job_id: str) -> dict[str, Any] | None:
    path = _state_path(job_id)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def output_path(job_id: str) -> Path:
    return _job_dir(job_id) / "output.mp4"

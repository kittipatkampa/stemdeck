from __future__ import annotations

import sys
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import modal

from app import job_state
from app.settings import (
    DATA_DIR,
    PIPELINE_ROOT,
    get_max_duration_sec,
    get_modal_app_name,
    get_pipeline_mode,
    modal_local_download,
    ytdlp_cookie_file,
)

if str(PIPELINE_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT.parent))

_active_local = 0
_active_lock = threading.Lock()
_runner: JobRunner | None = None
ACTIVE_JOB_TIMEOUT_SEC = 30 * 60

class JobRunner(ABC):
    @abstractmethod
    def start(self, job_id: str, url: str) -> None: ...

    @abstractmethod
    def get(self, job_id: str) -> dict[str, Any] | None: ...


class LocalRunner(JobRunner):
    def start(self, job_id: str, url: str) -> None:
        global _active_local
        with _active_lock:
            _active_local += 1

        def work() -> None:
            global _active_local
            try:
                from pipeline.progress import Stage, overall_progress
                from pipeline.stages import run_pipeline

                job_state.update_job(job_id, status="running")

                def report(stage: Stage, pct: float, extra: dict) -> None:
                    fields: dict[str, Any] = {
                        "status": "running",
                        "stage": stage,
                        "stage_progress": pct,
                        "overall_progress": extra.get(
                            "overall_progress", overall_progress(stage, pct)
                        ),
                    }
                    if extra.get("title"):
                        fields["title"] = extra["title"]
                    job_state.update_job(job_id, **fields)

                out = job_state.output_path(job_id)
                meta = run_pipeline(
                    url,
                    out,
                    work_dir=DATA_DIR / "jobs" / job_id / "work",
                    max_duration_sec=get_max_duration_sec(),
                    cookiefile=ytdlp_cookie_file(),
                    report=report,
                )
                job_state.update_job(
                    job_id,
                    status="done",
                    stage="combine",
                    stage_progress=1.0,
                    overall_progress=1.0,
                    title=meta.get("title"),
                )
            except Exception as e:
                job_state.update_job(job_id, status="failed", error=str(e))
            finally:
                with _active_lock:
                    _active_local -= 1

        threading.Thread(target=work, daemon=True).start()

    def get(self, job_id: str) -> dict[str, Any] | None:
        return job_state.get_job(job_id)


class ModalRunner(JobRunner):
    def __init__(self) -> None:
        self._dict = modal.Dict.from_name(f"{get_modal_app_name()}-jobs", create_if_missing=True)
        self._fn = modal.Function.from_name(get_modal_app_name(), "run_job")
        self._fn_stem_mux = modal.Function.from_name(
            get_modal_app_name(), "run_staged_job"
        )
        self._fn_uploaded = modal.Function.from_name(
            get_modal_app_name(), "run_uploaded_job"
        )

    def _set(self, job_id: str, **fields: Any) -> None:
        current = self._dict.get(job_id) or {}
        self._dict[job_id] = {**current, **fields, "updated_at": time.time()}

    def start(self, job_id: str, url: str) -> None:
        self._set(
            job_id,
            status="queued",
            stage="download",
            stage_progress=0.0,
            overall_progress=0.0,
            title=None,
            error=None,
            created_at=time.time(),
        )
        if modal_local_download():
            global _active_local
            with _active_lock:
                _active_local += 1
            threading.Thread(
                target=self._download_locally_then_modal,
                args=(job_id, url),
                daemon=True,
            ).start()
        else:
            self._fn.spawn(job_id, url)

    def reserve_upload(self, job_id: str, title: str) -> None:
        if self._dict.get(job_id) is not None:
            raise ValueError("Job already started")
        self._set(
            job_id,
            status="running",
            stage="download",
            stage_progress=0.0,
            overall_progress=0.0,
            title=title,
            error=None,
            created_at=time.time(),
        )

    def start_uploaded(self, job_id: str, source: Path, suffix: str) -> None:
        volume = modal.Volume.from_name(
            f"{get_modal_app_name()}-work", create_if_missing=True
        )
        with volume.batch_upload() as batch:
            batch.put_file(str(source), f"karaoke/jobs/{job_id}/source{suffix}")
        self._set(job_id, status="queued", stage_progress=1.0, overall_progress=0.2)
        self._fn_uploaded.spawn(job_id, suffix, get_max_duration_sec())

    def fail_upload(self, job_id: str, error: str) -> None:
        self._set(job_id, status="failed", error=error)

    def _download_locally_then_modal(self, job_id: str, url: str) -> None:
        global _active_local
        work = DATA_DIR / "jobs" / job_id / "staging"
        try:
            from pipeline.progress import Stage, overall_progress
            from pipeline.stages import download_video, extract_tracks, require_ffmpeg

            ffmpeg = require_ffmpeg()

            def report(stage: Stage, pct: float, extra: dict) -> None:
                fields: dict[str, Any] = {
                    "status": "running",
                    "stage": stage,
                    "stage_progress": pct,
                    "overall_progress": extra.get(
                        "overall_progress", overall_progress(stage, pct)
                    ),
                    "error": None,
                }
                if extra.get("title"):
                    fields["title"] = extra["title"]
                self._set(job_id, **fields)

            self._set(job_id, status="running")
            video_path, title, _vid = download_video(
                url,
                work / "dl",
                ffmpeg,
                report,
                ytdlp_cookie_file(),
                get_max_duration_sec(),
            )
            self._set(job_id, title=title)
            video_only, audio_wav = extract_tracks(
                ffmpeg, video_path, work / "extract", report
            )
            volume = modal.Volume.from_name(
                f"{get_modal_app_name()}-work", create_if_missing=True
            )
            remote_dir = f"karaoke/jobs/{job_id}"
            with volume.batch_upload() as batch:
                batch.put_file(str(audio_wav), f"{remote_dir}/audio.wav")
                batch.put_file(str(video_only), f"{remote_dir}/video_only.mp4")
            self._fn_stem_mux.remote(job_id)
        except Exception as e:
            self._set(job_id, status="failed", error=str(e))
        finally:
            with _active_lock:
                _active_local -= 1

    def get(self, job_id: str) -> dict[str, Any] | None:
        state = self._dict.get(job_id)
        if state is None:
            return None
        if self._is_stale(state):
            self._set(job_id, status="failed", error="Job timed out")
            state = self._dict.get(job_id)
        return {"job_id": job_id, **state}

    @staticmethod
    def _is_stale(state: dict[str, Any]) -> bool:
        if state.get("status") not in ("queued", "running"):
            return False
        updated_at = state.get("updated_at") or state.get("created_at")
        return not isinstance(updated_at, (int, float)) or time.time() - updated_at > ACTIVE_JOB_TIMEOUT_SEC

    def count_active(self) -> int:
        n = 0
        for _key, state in self._dict.items():
            if state.get("status") in ("queued", "running") and not self._is_stale(state):
                n += 1
        return n


def active_job_count() -> int:
    if get_pipeline_mode() == "modal":
        with _active_lock:
            local = _active_local
        runner = get_runner()
        if isinstance(runner, ModalRunner):
            return max(local, runner.count_active())
        return local
    return _active_local


def get_runner() -> JobRunner:
    global _runner
    if _runner is None:
        _runner = ModalRunner() if get_pipeline_mode() == "modal" else LocalRunner()
    return _runner

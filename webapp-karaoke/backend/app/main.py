from __future__ import annotations

import sys
import time
import uuid
from collections import defaultdict
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel, Field

from app import job_state
from app.access import access_code, is_authorized, require_access, unlock
from app.runner import active_job_count, get_runner
from app.settings import (
    PIPELINE_ROOT,
    get_frontend_origin,
    get_max_concurrent_jobs,
    get_pipeline_mode,
)
from app.storage import JobNotReadyError, gcs_signed_url, resolve_output_path

if str(PIPELINE_ROOT.parent) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT.parent))

from pipeline.errors import PipelineError
from pipeline.urls import validate_youtube_url

app = FastAPI(title="Karaoke API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_frontend_origin()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate: dict[str, list[float]] = defaultdict(list)
_RATE_WINDOW = 60.0
_RATE_MAX = 20


class CreateJobRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)


class AccessRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=256)


def _check_rate(ip: str) -> None:
    now = time.time()
    hits = [t for t in _rate[ip] if now - t < _RATE_WINDOW]
    _rate[ip] = hits
    if len(hits) >= _RATE_MAX:
        raise HTTPException(status_code=429, detail="Too many requests")
    _rate[ip].append(now)


def _public_state(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": raw.get("job_id"),
        "status": raw.get("status"),
        "stage": raw.get("stage"),
        "stage_progress": raw.get("stage_progress", 0.0),
        "overall_progress": raw.get("overall_progress", 0.0),
        "title": raw.get("title"),
        "error": raw.get("error"),
    }


@app.get("/healthz")
@app.get("/api/healthz")
def healthz() -> dict[str, str]:
    from app.settings import modal_local_download

    mode = get_pipeline_mode()
    payload: dict[str, str] = {"status": "ok", "pipeline": mode}
    if mode == "modal":
        payload["modal_local_download"] = "1" if modal_local_download() else "0"
    return payload


@app.get("/api/access")
def access_status(request: Request) -> dict[str, bool]:
    return {"required": bool(access_code()), "authorized": is_authorized(request)}


@app.post("/api/access")
def enter_access_code(req: AccessRequest, request: Request, response: Response) -> dict[str, bool]:
    _check_rate(request.client.host if request.client else "unknown")
    unlock(req.code, response)
    return {"authorized": True}


@app.post("/api/jobs", status_code=202, dependencies=[Depends(require_access)])
def create_job(req: CreateJobRequest, request: Request) -> dict[str, str]:
    _check_rate(request.client.host if request.client else "unknown")
    try:
        validate_youtube_url(req.url)
    except PipelineError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if active_job_count() >= get_max_concurrent_jobs():
        raise HTTPException(status_code=429, detail="Too many concurrent jobs")

    job_id = uuid.uuid4().hex[:12]
    if get_pipeline_mode() == "local":
        job_state.init_job(job_id, req.url)
    runner = get_runner()
    runner.start(job_id, req.url)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/jobs/{job_id}", dependencies=[Depends(require_access)])
def get_job_status(job_id: str) -> dict[str, Any]:
    runner = get_runner()
    state = runner.get(job_id)
    if state is None and get_pipeline_mode() == "local":
        state = job_state.get_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _public_state(state)


@app.get(
    "/api/jobs/{job_id}/download",
    response_model=None,
    dependencies=[Depends(require_access)],
)
def download_job(job_id: str) -> Response:
    runner = get_runner()
    state = runner.get(job_id)
    if state is None and get_pipeline_mode() == "local":
        state = job_state.get_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if state.get("status") != "done":
        raise HTTPException(status_code=409, detail="Job not ready")

    signed = gcs_signed_url(job_id)
    if signed:
        return RedirectResponse(signed, status_code=302)

    try:
        path = resolve_output_path(job_id)
    except JobNotReadyError:
        raise HTTPException(status_code=404, detail="Output file not found") from None

    filename = f"karaoke_{job_id}.mp4"
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

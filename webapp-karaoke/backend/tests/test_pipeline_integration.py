"""Slow local pipeline test (YouTube download + Demucs + mux)."""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_PIPELINE_INTEGRATION") != "1",
    reason="Set RUN_PIPELINE_INTEGRATION=1 to run full local pipeline (slow)",
)


def test_pipeline_produces_mp4():
    from pipeline.stages import run_pipeline

    out = ROOT / ".data" / "integration_test.mp4"
    work = ROOT / ".data" / "integration_work"
    work.mkdir(parents=True, exist_ok=True)
    if out.is_file():
        out.unlink()

    meta = run_pipeline(
        "https://youtube.com/shorts/senFAeo0RQM",
        out,
        work_dir=work,
    )
    assert out.is_file()
    assert out.stat().st_size > 100_000
    assert meta.get("video_id") == "senFAeo0RQM"

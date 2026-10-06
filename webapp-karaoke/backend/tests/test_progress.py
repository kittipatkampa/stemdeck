import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.progress import overall_progress


def test_overall_at_stage_start():
    assert overall_progress("download", 0.0) == 0.0
    assert overall_progress("stem", 0.0) == pytest.approx(0.30)


def test_overall_at_stage_end():
    assert overall_progress("download", 1.0) == 0.20
    assert overall_progress("combine", 1.0) == 1.0

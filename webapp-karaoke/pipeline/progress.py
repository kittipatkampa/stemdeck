from __future__ import annotations

from typing import Literal

Stage = Literal["download", "extract", "stem", "combine"]

STAGES: tuple[Stage, ...] = ("download", "extract", "stem", "combine")

# Initial weights from plan; tune after measuring timings.
STAGE_WEIGHTS: dict[Stage, float] = {
    "download": 0.20,
    "extract": 0.10,
    "stem": 0.55,
    "combine": 0.15,
}


def overall_progress(stage: Stage, stage_progress: float) -> float:
    """Map stage + 0..1 stage progress to 0..1 overall progress."""
    stage_progress = max(0.0, min(1.0, stage_progress))
    done_before = 0.0
    for s in STAGES:
        if s == stage:
            return done_before + STAGE_WEIGHTS[s] * stage_progress
        done_before += STAGE_WEIGHTS[s]
    return 1.0

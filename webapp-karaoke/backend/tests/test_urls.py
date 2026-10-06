import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest
from pipeline.errors import PipelineError
from pipeline.urls import validate_youtube_url


def test_shorts_url():
    assert (
        validate_youtube_url("https://youtube.com/shorts/senFAeo0RQM")
        == "https://www.youtube.com/watch?v=senFAeo0RQM"
    )


def test_watch_url():
    assert (
        validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


def test_youtu_be():
    assert (
        validate_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


def test_rejects_non_youtube():
    with pytest.raises(PipelineError):
        validate_youtube_url("https://example.com/video")


def test_rejects_empty():
    with pytest.raises(PipelineError):
        validate_youtube_url("   ")

from pathlib import Path

import pytest

from app import storage


class FakeVolume:
    def __init__(self, chunks):
        self.chunks = chunks
        self.requested_path = None

    def read_file(self, path):
        self.requested_path = path
        yield from self.chunks


def test_fetch_modal_output_uses_job_path_and_atomic_cache(monkeypatch, tmp_path: Path):
    volume = FakeVolume([b"\0\0\0\x18ftyp", b"mp42"])
    monkeypatch.setattr(storage.modal.Volume, "from_name", lambda *a, **k: volume)
    dest = tmp_path / "output.mp4"

    assert storage.fetch_modal_output("abc123", dest) == dest
    assert volume.requested_path == "karaoke/jobs/abc123/output.mp4"
    assert dest.read_bytes() == b"\0\0\0\x18ftypmp42"
    assert not dest.with_suffix(".download").exists()


def test_fetch_modal_output_does_not_cache_partial_download(monkeypatch, tmp_path: Path):
    def broken_chunks():
        yield b"partial"
        raise OSError("remote read failed")

    volume = FakeVolume(broken_chunks())
    monkeypatch.setattr(storage.modal.Volume, "from_name", lambda *a, **k: volume)
    dest = tmp_path / "output.mp4"

    with pytest.raises(storage.JobNotReadyError):
        storage.fetch_modal_output("abc123", dest)
    assert not dest.exists()
    assert not dest.with_suffix(".download").exists()

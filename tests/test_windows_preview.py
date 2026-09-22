"""Preview stamps must identify one commit and reject non-preview versions."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1]


@pytest.fixture
def preview_checkout(tmp_path):
    for name in (
        "scripts/windows/prepare-preview.py",
        "desktop/package.json",
        "desktop/src-tauri/tauri.conf.json",
        "desktop/src-tauri/Cargo.toml",
    ):
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / name, dest)
    (tmp_path / "static").mkdir()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Preview Test",
            "-c",
            "user.email=preview@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    return tmp_path


def test_preview_stamps_exact_commit_and_compatible_versions(preview_checkout):
    root = preview_checkout
    subprocess.run(
        [sys.executable, str(root / "scripts/windows/prepare-preview.py"), "0.17.3-alpha.1"],
        check=True,
    )
    meta = json.loads((root / "dist/build-metadata.json").read_text())
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    assert meta["commit"] == sha
    assert meta["pythonPackageVersion"] == "0.17.3a1"
    assert meta["desktopAcceptance"] == "pending"
    for name in (
        "desktop/package.json",
        "desktop/src-tauri/tauri.conf.json",
        "static/version.json",
    ):
        assert json.loads((root / name).read_text())["version"] == "0.17.3-alpha.1"
    assert 'version = "0.17.3-alpha.1"' in (root / "desktop/src-tauri/Cargo.toml").read_text()


@pytest.mark.parametrize(
    "version",
    [
        "0.17.3",
        "v0.17.3-alpha.1",
        "01.17.3-alpha.1",
        "0.17.3-alpha.01",
        "../preview",
        "0.17.3+fork",
    ],
)
def test_invalid_version_does_not_stamp_checkout(preview_checkout, version):
    root = preview_checkout
    result = subprocess.run(
        [sys.executable, str(root / "scripts/windows/prepare-preview.py"), version],
        capture_output=True,
    )
    assert result.returncode == 2
    assert not (root / "dist").exists()
    assert subprocess.check_output(["git", "diff"], cwd=root) == b""

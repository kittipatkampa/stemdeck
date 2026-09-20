"""Exercise a relocated, extracted ZIP. Run with CI Python, never install into the ZIP."""

import argparse
import ctypes
import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import psutil

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("version")
parser.add_argument("--logs", type=Path, required=True)
args = parser.parse_args()
root = args.package.resolve()
args.logs.mkdir(parents=True, exist_ok=True)
python = root / "python/Scripts/python.exe"
for name in (
    "StemDeck.exe",
    "portable.txt",
    "cpu-only",
    "python/runtime-version.json",
    "backend/static/js/videoSync.js",
    "backend/static/js/videoPlayback.js",
    "backend/jsruntime/qjs.exe",
    "README-WINDOWS.txt",
    "licenses",
):
    assert (root / name).exists(), name
assert " " in str(root)
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
base = f"http://127.0.0.1:{port}"
data = root / "data"
env = {
    **os.environ,
    "PYTHONNOUSERSITE": "1",
    "PYTHONHOME": str(root / "python/base"),
    "STEMDECK_DATA_DIR": str(data),
    "STEMDECK_JOBS_DIR": str(data / "jobs"),
    "STEMDECK_DEMUCS_DEVICE": "cpu",
    "STEMDECK_AUTO_SECTIONS": "0",
    "STEMDECK_BEAT_DETECTOR": "librosa",
    "STEMDECK_PERSIST_LIBRARY": "1",
}
fixture = args.logs / "fixture.mp4"
subprocess.run(
    [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=160x90:r=10",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=44100",
        "-t",
        "6",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(fixture),
    ],
    check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)


def request(path, **kwargs):
    return urllib.request.urlopen(urllib.request.Request(base + path, **kwargs), timeout=20)


# Hosted runners may launch Python without a console. CTRL_BREAK_EVENT
# requires the sender and the new process group to share one.
if os.name == "nt":
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if not kernel32.GetConsoleCP() and not kernel32.AllocConsole():
        raise ctypes.WinError(ctypes.get_last_error())

checks = []
children = []
proc = None
try:
    with (args.logs / "backend.log").open("w") as log:
        proc = subprocess.Popen(
            [
                str(python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--timeout-graceful-shutdown",
                "5",
            ],
            cwd=root / "backend",
            env=env,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        for _ in range(120):
            if proc.poll() is not None:
                raise RuntimeError(f"backend exited {proc.returncode}")
            try:
                health = json.load(request("/api/health"))
                break
            except (OSError, urllib.error.URLError):
                time.sleep(1)
        else:
            raise TimeoutError("backend startup")
        assert health["status"] == "ok" and health["version"] == args.version, health
        checks.append("relocated backend health and version")
        for path in (
            "/",
            "/js/videoPlayback.js",
            "/js/videoSync.js",
            "/js/releaseSource.js",
        ):
            assert request(path).status == 200, path
        checks.append("static assets including video and fork release discovery")
        boundary = "stemdeck-preview-fixture"
        body = (
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="fixture.mp4"\r\n'
                "Content-Type: video/mp4\r\n\r\n"
            ).encode()
            + fixture.read_bytes()
            + f"\r\n--{boundary}--\r\n".encode()
        )
        job = json.load(
            request(
                "/api/jobs",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
        )["job_id"]
        for _ in range(600):
            state = json.load(request(f"/api/jobs/{job}"))
            if state["status"] in ("done", "error", "cancelled"):
                break
            time.sleep(2)
        assert state["status"] == "done", state
        assert request(f"/api/jobs/{job}/stems/vocals.wav").status == 200
        with request(
            f"/api/jobs/{job}/video-track.mp4", headers={"Range": "bytes=0-127"}
        ) as response:
            assert response.status == 206
            assert len(response.read()) == 128
        checks.append("real MP4 import, CPU separation, stem serving and video Range requests")
        children = psutil.Process(proc.pid).children(recursive=True)
        proc.send_signal(signal.CTRL_BREAK_EVENT)
        proc.wait(timeout=30)
        # Uvicorn re-raises the console signal after its graceful shutdown.
        # The Windows CRT default signal handler returns 3; the console handler
        # can instead return STATUS_CONTROL_C_EXIT. Neither alone proves cleanup:
        # require the shutdown log and no surviving workers below as well.
        # https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/signal
        assert proc.returncode in (0, 3, 0xC000013A, -1073741510), proc.returncode
        for _ in range(15):
            if not any(child.is_running() for child in children):
                break
            time.sleep(1)
        assert not any(child.is_running() for child in children), "backend/worker survived shutdown"
        assert "Application shutdown complete." in (args.logs / "backend.log").read_text(
            encoding="utf-8", errors="replace"
        ), "backend did not complete graceful shutdown"
        checks.append("graceful shutdown without surviving child processes")
    result = {
        "automated": "passed",
        "checks": checks,
        "shutdownExitCode": proc.returncode,
        "desktopAcceptance": "pending",
    }
except BaseException as exc:
    result = {
        "automated": "failed",
        "checks": checks,
        "error": str(exc),
        "desktopAcceptance": "pending",
    }
    raise
finally:
    if proc and proc.poll() is None:
        for child in psutil.Process(proc.pid).children(recursive=True):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        proc.kill()
    for child in children:
        try:
            if child.is_running():
                child.kill()
        except psutil.NoSuchProcess:
            pass
    (args.logs / "validation.json").write_text(json.dumps(result, indent=2) + "\n")

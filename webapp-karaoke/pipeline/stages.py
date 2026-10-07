from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pipeline.errors import PipelineError
from pipeline.progress import Stage, overall_progress
from pipeline.urls import validate_youtube_url

ReportFn = Callable[[Stage, float, dict[str, Any]], None]

DEFAULT_MAX_DURATION_SEC = 600  # 10 minutes
DEMUCS_TQDM_RE = re.compile(r"(\d+)%\|")


def require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise PipelineError("ffmpeg is not on PATH")
    return ffmpeg


def pick_device(requested: str = "auto") -> str:
    import torch

    if requested != "auto":
        return requested
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _ytdlp_opts(dest_dir: Path, ffmpeg: str, cookiefile: str | None) -> dict:
    opts: dict[str, Any] = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "allowed_extractors": ["youtube"],
        "ffmpeg_location": str(Path(ffmpeg).parent),
    }
    if cookiefile and Path(cookiefile).is_file():
        opts["cookiefile"] = cookiefile
    return opts


def fetch_metadata(
    url: str,
    ffmpeg: str,
    max_duration_sec: int = DEFAULT_MAX_DURATION_SEC,
    cookiefile: str | None = None,
) -> dict[str, Any]:
    import yt_dlp
    from yt_dlp.utils import DownloadError

    canonical = validate_youtube_url(url)
    opts = _ytdlp_opts(Path(tempfile.gettempdir()), ffmpeg, cookiefile)
    opts["skip_download"] = True
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(canonical, download=False)
    except DownloadError as e:
        raise PipelineError(f"could not read video metadata: {e}") from e
    if info is None:
        raise PipelineError("could not read video metadata")
    duration = info.get("duration")
    if duration is not None and int(duration) > max_duration_sec:
        raise PipelineError(
            f"video is {int(duration)}s; maximum allowed is {max_duration_sec}s"
        )
    return info


def download_video(
    url: str,
    dest_dir: Path,
    ffmpeg: str,
    report: ReportFn | None = None,
    cookiefile: str | None = None,
    max_duration_sec: int = DEFAULT_MAX_DURATION_SEC,
) -> tuple[Path, str, str]:
    import yt_dlp
    from yt_dlp.utils import DownloadError

    canonical = validate_youtube_url(url)
    fetch_metadata(canonical, ffmpeg, max_duration_sec, cookiefile)
    dest_dir.mkdir(parents=True, exist_ok=True)

    def hook(d: dict) -> None:
        if report is None or d.get("status") != "downloading":
            return
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes") or 0
        if total:
            report("download", downloaded / total, {})

    opts = _ytdlp_opts(dest_dir, ffmpeg, cookiefile)
    opts["progress_hooks"] = [hook]
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(canonical, download=True)
    except DownloadError as e:
        raise PipelineError(f"download failed: {e}") from e
    if info is None:
        raise PipelineError("download failed: no metadata")
    video_id = str(info.get("id") or "")
    title = str(info.get("title") or video_id)
    path = _downloaded_path(info, dest_dir, video_id)
    if not path.is_file():
        raise PipelineError(f"download finished but file is missing: {path}")
    if report:
        report("download", 1.0, {"title": title})
    return path, title, video_id


def _downloaded_path(info: dict, dest_dir: Path, video_id: str) -> Path:
    requested = info.get("requested_downloads") or []
    if requested:
        filepath = requested[0].get("filepath")
        if filepath:
            return Path(filepath)
    for ext in ("mp4", "mkv", "webm"):
        candidate = dest_dir / f"{video_id}.{ext}"
        if candidate.is_file():
            return candidate
    return dest_dir / f"{video_id}.mp4"


def extract_tracks(
    ffmpeg: str,
    video_path: Path,
    work_dir: Path,
    report: ReportFn | None = None,
) -> tuple[Path, Path]:
    """Split into video-only MP4 and full-band audio WAV for Demucs."""
    work_dir.mkdir(parents=True, exist_ok=True)
    video_only = work_dir / "video_only.mp4"
    audio_wav = work_dir / "audio.wav"
    if report:
        report("extract", 0.0, {})

    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-map",
            "0:v",
            "-c",
            "copy",
            "-an",
            str(video_only),
        ],
        check=True,
    )
    subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            str(audio_wav),
        ],
        check=True,
    )
    if report:
        report("extract", 1.0, {})
    return video_only, audio_wav


def separate_vocals(
    audio_path: Path,
    out_dir: Path,
    model: str,
    device: str,
    report: ReportFn | None = None,
) -> Path:
    """Run Demucs two-stems vocals; returns no_vocals.wav."""
    import subprocess as sp
    import sys

    out_dir.mkdir(parents=True, exist_ok=True)
    if report:
        report("stem", 0.0, {})

    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems",
        "vocals",
        "-n",
        model,
        "-d",
        device,
        "--float32",
        "-o",
        str(out_dir),
        str(audio_path),
    ]
    proc = sp.Popen(
        cmd,
        stderr=sp.PIPE,
        stdout=sp.DEVNULL,
        text=True,
        bufsize=1,
    )
    assert proc.stderr is not None
    for line in proc.stderr:
        m = DEMUCS_TQDM_RE.search(line)
        if m and report:
            report("stem", int(m.group(1)) / 100.0, {})
    code = proc.wait()
    if code != 0:
        raise PipelineError(f"demucs failed with exit code {code}")

    stem_name = audio_path.stem
    no_vocals = out_dir / model / stem_name / "no_vocals.wav"
    if not no_vocals.is_file():
        no_vocals = out_dir / model / audio_path.stem / "no_vocals.wav"
    if not no_vocals.is_file():
        raise PipelineError("demucs did not write no_vocals.wav")
    if report:
        report("stem", 1.0, {})
    return no_vocals


def _mux_cmd(
    ffmpeg: str,
    video_path: Path,
    audio_path: Path,
    dest: Path,
    video_codec: list[str],
    *,
    progress: bool,
) -> list[str]:
    cmd = [
        ffmpeg,
        "-nostdin",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v",
        "-map",
        "1:a",
        *video_codec,
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    if progress:
        cmd[5:5] = ["-progress", "pipe:1"]
    return cmd


def mux_karaoke(
    ffmpeg: str,
    video_path: Path,
    audio_path: Path,
    dest: Path,
    report: ReportFn | None = None,
) -> None:
    if not video_path.is_file():
        raise PipelineError(f"mux missing video: {video_path}")
    if not audio_path.is_file():
        raise PipelineError(f"mux missing audio: {audio_path}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if report:
        report("combine", 0.0, {})

    video_codecs: list[tuple[str, list[str]]] = [
        ("copy", ["-c:v", "copy"]),
        (
            "libx264",
            ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p"],
        ),
    ]
    last_err = ""
    for idx, (_name, vcodec) in enumerate(video_codecs):
        use_progress = idx == 0 and report is not None
        cmd = _mux_cmd(ffmpeg, video_path, audio_path, dest, vcodec, progress=use_progress)
        if use_progress:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            duration_us: int | None = None
            out_us = 0
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("duration="):
                    try:
                        duration_us = int(float(line.split("=", 1)[1]) * 1_000_000)
                    except ValueError:
                        pass
                elif line.startswith("out_time_us="):
                    try:
                        out_us = int(line.split("=", 1)[1])
                    except ValueError:
                        pass
                if duration_us and duration_us > 0 and report:
                    report("combine", min(1.0, out_us / duration_us), {})
            stderr = proc.stderr.read() if proc.stderr else ""
            code = proc.wait()
        else:
            result = subprocess.run(cmd, capture_output=True, text=True)
            code = result.returncode
            stderr = result.stderr

        if code == 0 and dest.is_file():
            if report:
                report("combine", 1.0, {})
            return
        last_err = (stderr or "").strip() or f"exit code {code}"
        if dest.is_file():
            dest.unlink(missing_ok=True)

    raise PipelineError(f"ffmpeg mux failed: {last_err}")


def run_pipeline(
    url: str,
    output_mp4: Path,
    *,
    work_dir: Path | None = None,
    model: str = "htdemucs",
    device: str = "auto",
    cookiefile: str | None = None,
    max_duration_sec: int = DEFAULT_MAX_DURATION_SEC,
    report: ReportFn | None = None,
) -> dict[str, str]:
    """Run all stages; writes output_mp4 and returns metadata."""
    ffmpeg = require_ffmpeg()
    ffmpeg_dir = str(Path(ffmpeg).parent)
    path_env = os.environ.get("PATH", "")
    if ffmpeg_dir not in path_env.split(os.pathsep):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + path_env

    resolved_device = pick_device(device)

    def wrapped_report(stage: Stage, pct: float, extra: dict[str, Any]) -> None:
        if report:
            report(
                stage,
                pct,
                {
                    **extra,
                    "overall_progress": overall_progress(stage, pct),
                },
            )

    if work_dir is None:
        with tempfile.TemporaryDirectory(prefix="karaoke-") as tmp:
            return _run_in_work(
                url,
                output_mp4,
                Path(tmp),
                ffmpeg,
                model,
                resolved_device,
                cookiefile,
                max_duration_sec,
                wrapped_report,
            )
    return _run_in_work(
        url,
        output_mp4,
        work_dir,
        ffmpeg,
        model,
        resolved_device,
        cookiefile,
        max_duration_sec,
        wrapped_report,
    )


def _run_in_work(
    url: str,
    output_mp4: Path,
    work: Path,
    ffmpeg: str,
    model: str,
    device: str,
    cookiefile: str | None,
    max_duration_sec: int,
    report: ReportFn,
) -> dict[str, str]:
    video_path, title, video_id = download_video(
        url,
        work / "dl",
        ffmpeg,
        report,
        cookiefile,
        max_duration_sec,
    )
    video_only, audio_wav = extract_tracks(ffmpeg, video_path, work / "extract", report)
    no_vocals = separate_vocals(audio_wav, work / "stems", model, device, report)
    mux_karaoke(ffmpeg, video_only, no_vocals, output_mp4, report)
    return {"title": title, "video_id": video_id}

#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#   "yt-dlp>=2026.7.4",
#   "demucs>=4.0.1,<4.1",
#   "torch>=2.6,<2.7; sys_platform != 'darwin' or platform_machine != 'x86_64'",
#   "torchaudio>=2.6,<2.7; sys_platform != 'darwin' or platform_machine != 'x86_64'",
#   "torch>=2.2,<2.3; sys_platform == 'darwin' and platform_machine == 'x86_64'",
#   "torchaudio>=2.2,<2.3; sys_platform == 'darwin' and platform_machine == 'x86_64'",
#   "soundfile>=0.12",
# ]
# ///
"""Download a YouTube video, strip vocals with Demucs, mux a karaoke MP4.

Standalone: no StemDeck server. Run with:

    uv run scripts/karaoke.py https://youtube.com/shorts/VIDEO_ID
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
        "www.youtube-nocookie.com",
    }
)

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
UNSAFE_CHARS = re.compile(r"[^\w.-]+", re.UNICODE)


class KaraokeError(Exception):
    """User-facing failure with a non-zero exit."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a YouTube video and write a vocal-free karaoke MP4.",
    )
    parser.add_argument("url", help="YouTube video or Shorts URL")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("karaoke_out"),
        help="Directory for the karaoke MP4 (default: ./karaoke_out)",
    )
    parser.add_argument(
        "--keep-stems",
        action="store_true",
        help="Keep downloaded video and Demucs WAV stems next to the MP4",
    )
    parser.add_argument(
        "--model",
        default="htdemucs",
        help="Demucs model name (default: htdemucs). htdemucs_ft is slower and cleaner.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=("auto", "mps", "cuda", "cpu"),
        help="Torch device (default: auto)",
    )
    return parser.parse_args(argv)


def require_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise KaraokeError("ffmpeg is not on PATH. Install ffmpeg and try again.")
    try:
        subprocess.run(
            [ffmpeg, "-hide_banner", "-version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        raise KaraokeError(f"ffmpeg at {ffmpeg} could not be executed: {e}") from e
    except subprocess.CalledProcessError as e:
        raise KaraokeError(
            f"ffmpeg at {ffmpeg} is installed but failed to run (exit {e.returncode})"
        ) from e
    return ffmpeg


def validate_youtube_url(url: str) -> str:
    raw = url.strip()
    if not raw:
        raise KaraokeError("URL is required")
    try:
        parsed = urllib.parse.urlparse(raw)
    except ValueError as e:
        raise KaraokeError(f"could not parse URL: {e}") from e
    if parsed.scheme not in ("http", "https"):
        raise KaraokeError("URL must use http or https")
    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        raise KaraokeError(f"unsupported host: {host or '(empty)'} (YouTube only)")
    video_id = extract_video_id(parsed, host)
    if video_id is None:
        raise KaraokeError("could not extract a video ID from URL")
    return f"https://www.youtube.com/watch?v={video_id}"


def extract_video_id(parsed: urllib.parse.ParseResult, host: str) -> str | None:
    query = urllib.parse.parse_qs(parsed.query)
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/", 1)[0]
        return candidate if VIDEO_ID_RE.match(candidate) else None
    parts = [p for p in parsed.path.split("/") if p]
    if "shorts" in parts:
        idx = parts.index("shorts")
        if idx + 1 < len(parts) and VIDEO_ID_RE.match(parts[idx + 1]):
            return parts[idx + 1]
    if "embed" in parts:
        idx = parts.index("embed")
        if idx + 1 < len(parts) and VIDEO_ID_RE.match(parts[idx + 1]):
            return parts[idx + 1]
    if "watch" in parts or parsed.path in ("", "/"):
        values = query.get("v", [])
        if values and VIDEO_ID_RE.match(values[0]):
            return values[0]
    if parts and VIDEO_ID_RE.match(parts[-1]):
        return parts[-1]
    return None


def pick_device(requested: str) -> str:
    import torch

    if requested != "auto":
        return requested
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def slugify(title: str, video_id: str) -> str:
    slug = UNSAFE_CHARS.sub("_", title).strip("._")
    slug = re.sub(r"_+", "_", slug)
    if not slug:
        slug = video_id
    return f"{slug[:80]}_{video_id}"


def download_video(url: str, dest_dir: Path, ffmpeg: str) -> tuple[Path, str, str]:
    import yt_dlp
    from yt_dlp.utils import DownloadError

    dest_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": str(dest_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": False,
        "no_warnings": False,
        "restrictfilenames": True,
        "allowed_extractors": ["youtube"],
        "ffmpeg_location": str(Path(ffmpeg).parent),
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as e:
        raise KaraokeError(f"download failed: {e}") from e
    except Exception as e:
        raise KaraokeError(f"download failed: {e}") from e

    if info is None:
        raise KaraokeError("download failed: no video metadata returned")
    video_id = str(info.get("id") or "")
    title = str(info.get("title") or video_id)
    path = _downloaded_path(info, dest_dir, video_id)
    if not path.is_file():
        raise KaraokeError(f"download finished but file is missing: {path}")
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


def separate_vocals(video_path: Path, out_dir: Path, model: str, device: str) -> Path:
    from demucs.separate import main as demucs_main

    out_dir.mkdir(parents=True, exist_ok=True)
    argv = [
        "--two-stems",
        "vocals",
        "-n",
        model,
        "-d",
        device,
        "--float32",
        "-o",
        str(out_dir),
        str(video_path),
    ]
    try:
        demucs_main(argv)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        if code:
            raise KaraokeError(f"demucs failed with exit code {code}") from e
    except Exception as e:
        raise KaraokeError(f"stem separation failed: {e}") from e

    no_vocals = out_dir / model / video_path.stem / "no_vocals.wav"
    if not no_vocals.is_file():
        raise KaraokeError(f"demucs did not write {no_vocals}")
    return no_vocals


def mux_karaoke(ffmpeg: str, video_path: Path, audio_path: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
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
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise KaraokeError(f"ffmpeg mux failed with exit code {e.returncode}") from e


def copy_stems(stem_wav: Path, dest_dir: Path, slug: str) -> None:
    stems_dir = dest_dir / f"{slug}_stems"
    stems_dir.mkdir(parents=True, exist_ok=True)
    for wav in stem_wav.parent.glob("*.wav"):
        shutil.copy2(wav, stems_dir / wav.name)


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        ffmpeg = require_ffmpeg()
        ffmpeg_dir = str(Path(ffmpeg).parent)
        path = os.environ.get("PATH", "")
        if ffmpeg_dir not in path.split(os.pathsep):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + path
        url = validate_youtube_url(args.url)
        device = pick_device(args.device)
        output_dir = args.output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"device: {device}", flush=True)
        print(f"model:  {args.model}", flush=True)

        with tempfile.TemporaryDirectory(prefix="karaoke-") as tmp:
            tmp_path = Path(tmp)
            print("downloading...", flush=True)
            video_path, title, video_id = download_video(url, tmp_path / "dl", ffmpeg)
            slug = slugify(title, video_id)
            print(f"separating vocals ({args.model} on {device})...", flush=True)
            no_vocals = separate_vocals(video_path, tmp_path / "stems", args.model, device)
            dest = output_dir / f"{slug}_karaoke.mp4"
            print("muxing karaoke MP4...", flush=True)
            mux_karaoke(ffmpeg, video_path, no_vocals, dest)
            if args.keep_stems:
                copy_stems(no_vocals, output_dir, slug)
                shutil.copy2(video_path, output_dir / f"{slug}_source{video_path.suffix}")

        print(dest)
        print(dest.as_uri())
        return 0
    except KaraokeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())

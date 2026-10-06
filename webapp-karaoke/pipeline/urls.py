"""YouTube URL validation (from scripts/karaoke.py)."""

from __future__ import annotations

import re
import urllib.parse

from pipeline.errors import PipelineError

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


def validate_youtube_url(url: str) -> str:
    raw = url.strip()
    if not raw:
        raise PipelineError("URL is required")
    if len(raw) > 2048:
        raise PipelineError("URL is too long")
    try:
        parsed = urllib.parse.urlparse(raw)
    except ValueError as e:
        raise PipelineError(f"could not parse URL: {e}") from e
    if parsed.scheme not in ("http", "https"):
        raise PipelineError("URL must use http or https")
    host = (parsed.hostname or "").lower()
    if host not in YOUTUBE_HOSTS:
        raise PipelineError(f"unsupported host: {host or '(empty)'} (YouTube only)")
    video_id = extract_video_id(parsed, host)
    if video_id is None:
        raise PipelineError("could not extract a video ID from URL")
    return f"https://www.youtube.com/watch?v={video_id}"

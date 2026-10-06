"""Phase 0: verify yt-dlp can download the test Short from Modal's network."""

import modal

app = modal.App("karaoke-spike-download")

image = (
    modal.Image.from_registry("debian:bookworm-slim", add_python="3.11")
    .apt_install("ffmpeg")
    .pip_install("yt-dlp>=2026.7.4")
)

TEST_URL = "https://youtube.com/shorts/senFAeo0RQM"


@app.function(image=image, timeout=300)
def download_spike(url: str = TEST_URL) -> dict:
    import yt_dlp
    from yt_dlp.utils import DownloadError

    opts = {
        "format": "bv*+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": "/tmp/%(id)s.%(ext)s",
        "noplaylist": True,
        "quiet": True,
        "allowed_extractors": ["youtube"],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as e:
        return {"ok": False, "error": str(e)}
    video_id = str(info.get("id") or "")
    title = str(info.get("title") or "")
    duration = info.get("duration")
    return {
        "ok": True,
        "video_id": video_id,
        "title": title,
        "duration": duration,
    }


@app.local_entrypoint()
def main():
    result = download_spike.remote()
    print(result)

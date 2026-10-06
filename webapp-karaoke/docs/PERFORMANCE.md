# Performance notes

Recorded during initial implementation (Oct 2026).

## Phase 0 — Modal yt-dlp spike

- **Test URL:** `https://youtube.com/shorts/senFAeo0RQM`
- **Result:** Failed on Modal datacenter IP with YouTube bot check (`Sign in to confirm you're not a bot`).
- **Mitigation:** Provide `youtube-cookies` Modal secret with `YTDLP_COOKIES_B64`, or use `PIPELINE=local` for development on a residential IP.

## Stage weights (initial)

| Stage   | Weight |
|---------|--------|
| download | 20% |
| extract  | 10% |
| stem     | 55% |
| combine  | 15% |

Tune after measuring real jobs on local MPS and Modal T4.

## Local integration (MPS, test Short)

- **URL:** `https://youtube.com/shorts/senFAeo0RQM`
- **Wall time:** ~21s end-to-end on Apple Silicon (download + extract + Demucs + mux)
- **Output:** `webapp-karaoke/.data/integration_test.mp4` (>100 KB)

## Reference output

The standalone CLI already produced a karaoke MP4 for the test Short under repo `karaoke_out/`. Compare duration and subjective vocal removal when validating the web app pipeline.

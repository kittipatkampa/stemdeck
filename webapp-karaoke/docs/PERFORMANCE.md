# Performance notes

Recorded during initial implementation (Oct 2026).

## Phase 0 — Modal yt-dlp spike

- **Test URL:** `https://youtube.com/shorts/senFAeo0RQM`
- **Result:** Failed on Modal datacenter IP with YouTube bot check (`Sign in to confirm you're not a bot`).
- **Working route:** `PIPELINE=local` or the locally hosted hybrid mode downloads on this Mac before sending extracted tracks to Modal.

The dedicated cookies were installed on 2026-10-06. They work from this Mac, but production Modal URL jobs failed at metadata lookup with “The page needs to be reloaded.” Pinning yt-dlp to the locally working `2026.8.19` release and trying the documented `web_embedded` player client did not resolve the Modal failure. The public URL app now uses a GCP download job with yt-dlp[default], EJS, Deno, and dedicated cookies; device file upload remains available.

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

## Production Modal hybrid smoke test

- **Job:** `a04fe3cb179d` on `karaoke-maker-prod`, 2026-10-06
- **Result:** Done; status polling and full MP4 download checks passed after downloading and extracting on this Mac.
- **Test wall time:** 55.06 seconds, including polling and download validation. This is not a per-stage benchmark.

## Public device-file smoke test

- **Job:** `87ea3a17d655` on `karaoke-maker-prod`, 2026-10-06
- **Input:** 21 MB source MP4 saved on the local device
- **Result:** GCS browser CORS preflight and direct PUT passed; public API completed the upload, Modal reached `done`, and the Cloud Run proxy returned 206 with MP4 bytes for a range request.
- **Limit:** This tested one small input through the public URL. Phone file-picker behavior and near-limit 500 MB transfers remain untested.

## Public YouTube URL jobs

- **Short:** `1f00211a9ef5`, 2026-10-06. GCP download, private GCS, Modal stem/mux, and 206 MP4 range response passed.
- **Three-minute video:** `69eea516931d`, 2026-10-06, URL `https://www.youtube.com/watch?v=SgDqxwZdjmw`. GCP download, GCS, Modal, and full MP4 download passed. FFprobe found 180.29 seconds, AV1 video, AAC audio, and 18,939,848 output bytes.
- **Limit:** This establishes two successful public URL inputs, not general reliability across YouTube or near-limit 10-minute/500 MB files.

## Reference output

The standalone CLI already produced a karaoke MP4 for the test Short under repo `karaoke_out/`. Compare duration and subjective vocal removal when validating the web app pipeline.

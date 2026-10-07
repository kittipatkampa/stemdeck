FROM denoland/deno:bin-2.9.7 AS deno

FROM python:3.11-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=deno /deno /usr/local/bin/deno
RUN pip install --no-cache-dir \
    'yt-dlp[default]==2026.8.19' \
    'google-cloud-storage>=2.18' \
    'modal==1.6.1'
COPY pipeline /app/pipeline
COPY deploy/youtube-downloader/worker.py /app/worker.py
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1
WORKDIR /app
CMD ["python", "/app/worker.py"]

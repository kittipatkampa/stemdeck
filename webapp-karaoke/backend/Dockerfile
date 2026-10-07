FROM python:3.11-slim-bookworm

WORKDIR /app

COPY backend/pyproject.toml /app/backend/
COPY pipeline /app/pipeline
COPY backend/app /app/backend/app

RUN pip install --no-cache-dir uv \
  && cd /app/backend && uv pip install --system .

ENV PYTHONPATH=/app
WORKDIR /app/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

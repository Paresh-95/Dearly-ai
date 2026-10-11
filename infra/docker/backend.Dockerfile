FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# System deps for ingestion: ffmpeg (video -> audio extraction), tesseract-ocr (best-effort
# image OCR, never required for a job to succeed), libmagic (upload content-type sniffing).
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg tesseract-ocr libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
RUN useradd --create-home app \
    && mkdir -p /app/data/uploads && chown -R app /app
USER app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
# Apply migrations, then serve. (A dedicated migrate job is preferable in production.)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

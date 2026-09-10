FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (ffmpeg and libsndfile are required for audio processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reproducible dependency installs
COPY --from=ghcr.io/astral-sh/uv:0.12.12 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install python dependencies from the lockfile into /app/.venv (no dev dependencies in the image)
COPY pyproject.toml uv.lock .
RUN uv sync --locked --no-dev --no-cache

# Copy application source only -- tests/ has no reason to ship in the runtime image
# (pytest itself isn't even installed here, since --no-dev above skips it).
COPY app/ ./app/

# Run as a non-root user rather than the container's default root. uploads/data/hf-cache
# are the only paths written at runtime (docker-compose.yml mounts named volumes over
# them; Docker seeds a fresh volume's ownership from whatever's already at that path in
# the image, so this carries through to the real persisted volumes too), so only those
# plus /app itself (for the DATABASE_PATH default of a relative "auralis.db" when not
# running under compose) need to be writable by appuser -- app/ and .venv/ stay
# root-owned but world-readable, which is all a non-root process needs to run them.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && mkdir -p uploads data hf-cache \
    && chown -R appuser:appuser /app/uploads /app/data /app/hf-cache \
    && chown appuser:appuser /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

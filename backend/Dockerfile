# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Bring in the uv binary from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first for better layer caching (changes rarely).
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install the application itself.
COPY README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# A simple, dependency-free liveness probe against the health endpoint.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import os,urllib.request,sys; port=os.environ.get('PORT','8000'); sys.exit(0 if urllib.request.urlopen(f'http://localhost:{port}/health').status==200 else 1)"

# PaaS hosts (HF Spaces, Render) inject PORT; default to 8000 for compose/local.
CMD ["sh", "-c", "uvicorn aletheia.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

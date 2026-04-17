# Stage 1: Build
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app

# Install dependencies into .venv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and sync project
COPY src/ ./src/
COPY pipeline.py ./
COPY pyproject.toml uv.lock README.md ./

RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    HEADLESS=true \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Copy built virtual environment and source code
COPY --from=builder /app /app

# Put virtual environment in PATH
ENV PATH="/app/.venv/bin:$PATH"

# Install Playwright browsers and OS dependencies
RUN playwright install --with-deps chromium

CMD ["python", "pipeline.py"]

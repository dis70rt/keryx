FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS deps-builder
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM deps-builder AS app-builder

COPY src/ ./src/
COPY pipeline.py ./
COPY README.md ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    HEADLESS=false \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=deps-builder /app/.venv /app/.venv

RUN playwright install --with-deps chromium

COPY --from=app-builder /app /app

CMD ["python", "pipeline.py"]
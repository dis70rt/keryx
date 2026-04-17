FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock* ./
COPY . .

RUN uv sync --frozen --no-dev

RUN uv run playwright install --with-deps chromium

CMD ["uv", "run", "python", "pipeline.py"]

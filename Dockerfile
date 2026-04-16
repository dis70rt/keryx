# Use a slim Python 3.12 image
FROM python:3.12-slim

# Enforce non-interactive installation and unbuffered output
ENV PYTHONUNBUFFERED=1
ENV HEADLESS=true
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install basic utils required for Playwright OS dependencies fetching and UV
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install 'uv' for rapid dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Copy all code
COPY . .

# Setup virtualenv inside container and install
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install -e .

# Install the Chromium browser and its system-level dependencies for Playwright
RUN playwright install --with-deps chromium

# Keep the container running or run a default task
CMD ["python", "-c", "import time; print('Container ready. Used for scraping tasks.'); time.sleep(86400)"]

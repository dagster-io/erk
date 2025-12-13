# Dockerfile for all Compass production services
#
# This single image supports all Compass services:
#   - slackbot (default)
#   - compass-admin
#   - compass-temporal-worker
#
# Override the CMD in render.yaml using `dockerCommand` to run different services

FROM public.ecr.aws/docker/library/python:3.13-slim

# Install system dependencies, uv, Rust, and Node.js in a single layer
RUN apt-get update && apt-get install -y \
    libpq-dev \
    procps \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g yarn \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /app

# Copy workspace configuration and install dependencies in a single layer
COPY pyproject.toml uv.lock ./
COPY packages/ packages/
RUN uv sync --frozen --no-dev && uv pip install py-spy

# Build frontend
COPY scripts/build-ui.sh scripts/build-ui.sh
RUN chmod +x scripts/build-ui.sh && ./scripts/build-ui.sh

# Build admin panel
COPY scripts/build-admin-ui.sh scripts/build-admin-ui.sh
RUN chmod +x scripts/build-admin-ui.sh && ./scripts/build-admin-ui.sh

# Set environment variables
ENV PORT=10000 \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# run it like this:
# CMD ["slackbot", "start", "--config", "..."]

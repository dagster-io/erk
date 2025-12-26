# Dockerfile for all Compass staging services
#
# This single image supports all Compass services:
#   - slackbot (default)
#   - compass-admin
#   - compass-temporal-worker
#
# Override the CMD in render.yaml using `dockerCommand` to run different services

FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv

# Install Rust toolchain (required for some Python dependencies)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install Node.js 20.x and yarn (required for frontend build)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g yarn && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy workspace configuration
COPY pyproject.toml .
COPY uv.lock .

# Copy all packages (needed for workspace dependencies)
COPY packages/ packages/

# Install all dependencies using uv
RUN uv sync --frozen --no-dev

# Build frontend
COPY scripts/build-ui.sh scripts/build-ui.sh
RUN chmod +x scripts/build-ui.sh && ./scripts/build-ui.sh

# Copy staging config
COPY staging.csbot.config.yaml .

# Expose ports (slackbot uses 10000, admin panel uses 8080)
EXPOSE 10000 8080

# Set default port environment variable
ENV PORT=10000

# Default command: run slackbot
# Override with dockerCommand in render.yaml for other services
CMD ["uv", "run", "--frozen", "slackbot", "start", "--config", "staging.csbot.config.yaml"]

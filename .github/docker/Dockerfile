FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv (recommended: copy from official image)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Pre-install Python 3.11 for uv tool environments
RUN uv python install 3.11

# Install Claude Code
ENV PATH="/root/.local/bin:${PATH}"
RUN curl -fsSL https://claude.ai/install.sh | bash

# Install npm tools
RUN npm install -g prettier@3.6.0 @withgraphite/graphite-cli

# Verify installations
RUN uv --version && python3.11 --version && claude --version && prettier --version && gt --version

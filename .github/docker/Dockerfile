FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies (as root)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ca-certificates \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 (as root - system-wide)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install uv (as root - to /usr/local/bin)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Install npm tools globally (as root - accessible to all users)
RUN npm install -g prettier@3.6.0 @withgraphite/graphite-cli

# Create non-root user for Claude Code operations
RUN useradd -m -s /bin/bash ci-user \
    && echo "ci-user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/ci-user

# Configure git safe.directory globally to avoid ownership errors
# (GitHub Actions checkout runs as root but commands run as ci-user)
RUN git config --system --add safe.directory '*'

# Switch to non-root user for remaining installations
USER ci-user
WORKDIR /home/ci-user

# Set up PATH for ci-user's local binaries
ENV PATH="/home/ci-user/.local/bin:${PATH}"

# Pre-install Python 3.11 for uv tool environments (as ci-user)
RUN uv python install 3.11

# Install Claude Code (as ci-user - goes to ~/.local/bin)
RUN curl -fsSL https://claude.ai/install.sh | bash

# Verify installations
RUN uv --version && python3.11 --version && claude --version && prettier --version && gt --version

# Set default working directory to /github/workspace (where Actions mounts repo)
WORKDIR /github/workspace

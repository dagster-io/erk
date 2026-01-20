# Local Development Docker Image for Erk
#
# This image is designed for running Claude Code in isolated implementation mode.
# It provides filesystem isolation - Claude can only access the mounted worktree.
#
# Build: docker build -t erk-local -f .erk/docker/Dockerfile .
# Usage: See `erk implement --docker` for automatic orchestration
#
# Key differences from CI image (.github/docker/Dockerfile):
# - Optimized for interactive TTY use
# - Same user (ci-user) for --dangerously-skip-permissions compatibility

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install base dependencies (as root)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ca-certificates \
    sudo \
    openssh-client \
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
# UID 1001 is used - when running with --user $(id -u):$(id -g) the container
# can read/write host files correctly while Claude Code remains in PATH
RUN useradd -m -s /bin/bash -u 1001 ci-user \
    && echo "ci-user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/ci-user

# Configure git safe.directory globally to avoid ownership errors
# This allows git operations when running with different host UIDs
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

# Set default working directory to /workspace (where worktree is mounted)
WORKDIR /workspace

# Default command - interactive shell for debugging
# Real usage: docker run ... claude --dangerously-skip-permissions /erk:plan-implement
CMD ["/bin/bash"]

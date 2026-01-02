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

# Install uv
ENV CARGO_HOME=/usr/local/cargo
ENV PATH="${CARGO_HOME}/bin:${PATH}"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Claude Code
ENV CLAUDE_HOME=/usr/local/claude
ENV PATH="${CLAUDE_HOME}/local:${PATH}"
RUN mkdir -p ${CLAUDE_HOME} \
    && curl -fsSL https://claude.ai/install.sh | CLAUDE_INSTALL_DIR=${CLAUDE_HOME} bash

# Install npm tools
RUN npm install -g prettier@3.6.0 @withgraphite/graphite-cli

# Verify installations
RUN uv --version && claude --version && prettier --version && gt --version

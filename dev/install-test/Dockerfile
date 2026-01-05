# Docker image for manual installation testing
# Full toolchain: Python 3.11, git, uv, gh, gt, claude
#
# Build: docker build -t erk-install-test dev/install-test/
# Run:   docker run -it --rm -v $(PWD):/home/testuser/erk-source:ro erk-install-test shell

FROM python:3.11-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Install GitHub CLI (gh)
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Install Graphite CLI (gt)
# Note: gt requires Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g @withgraphite/graphite-cli \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI
# Note: Claude CLI is installed via npm
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user for testing
RUN useradd -m -s /bin/bash testuser
USER testuser
WORKDIR /home/testuser

# Re-install uv for testuser (it was installed for root)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/testuser/.local/bin:$PATH"

# Copy fixtures
COPY --chown=testuser:testuser fixtures/ /home/testuser/fixtures/

# Copy entrypoint
COPY --chown=testuser:testuser entrypoint.sh /home/testuser/entrypoint.sh
RUN chmod +x /home/testuser/entrypoint.sh

ENTRYPOINT ["/home/testuser/entrypoint.sh"]
CMD ["shell"]

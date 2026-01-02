---
title: Container-less CI with Native Tool Installation
read_when:
  - Setting up Claude Code in GitHub Actions without containers
  - Comparing container vs container-less CI approaches
  - Choosing between container and container-less CI approaches
---

# Container-less CI with Native Tool Installation

## Overview

This document covers the container-less approach for running Claude Code in GitHub Actions. For the container-based alternative, see [claude-code-docker.md](claude-code-docker.md).

**Pros:** No image maintenance, simpler workflow, no permission workarounds needed.

**Cons:** Longer install time per run (~30s), network dependency, potential version drift.

## Workflow Pattern

The native installation pattern installs tools directly on the `ubuntu-latest` runner:

```yaml
jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    permissions:
      contents: read
      pull-requests: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install Claude Code
        run: |
          curl -fsSL https://claude.ai/install.sh | bash
          echo "$HOME/.claude/local/bin" >> $GITHUB_PATH

      - name: Install erk
        run: uv tool install --from . --with ./packages/erk-shared erk

      - name: Run Claude Code
        env:
          CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ github.token }}
        run: |
          claude --print \
            --model claude-opus-4-5 \
            --allowedTools 'Bash(gh:*),Bash(erk exec:*),Read(*)' \
            --dangerously-skip-permissions \
            --output-format stream-json \
            --verbose \
            "Your prompt here"
```

## Key Components

### 1. uv Installation

Uses the official `astral-sh/setup-uv@v5` action for fast, cached Python package management:

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v5
```

### 2. Claude Code Installation

Installs Claude Code via the official installer script and adds it to PATH:

```yaml
- name: Install Claude Code
  run: |
    curl -fsSL https://claude.ai/install.sh | bash
    echo "$HOME/.claude/local/bin" >> $GITHUB_PATH
```

The `$GITHUB_PATH` append ensures Claude Code is available in subsequent steps.

### 3. erk Installation

Installs erk as a uv tool with local packages:

```yaml
- name: Install erk
  run: uv tool install --from . --with ./packages/erk-shared erk
```

### 4. --dangerously-skip-permissions Flag

Required for non-interactive CI execution. Unlike the container approach, this works on ubuntu-latest because the runner executes as a non-root user (UID typically 1001).

## Comparison: Container vs Container-less

| Aspect               | Container                                | Container-less            |
| -------------------- | ---------------------------------------- | ------------------------- |
| **Setup complexity** | High (Dockerfile, registry, credentials) | Low (direct installation) |
| **Startup time**     | Variable (image pull)                    | Fast (no image pull)      |
| **Tool versions**    | Fixed at image build                     | Always latest             |
| **Maintenance**      | Image rebuilds required                  | None                      |
| **Permissions**      | Complex (root user workarounds)          | Simple (runs as non-root) |
| **Consistency**      | High (identical environment)             | Medium (runner updates)   |
| **Package registry** | Required (GHCR auth)                     | Not required              |

### Container-less Advantages

- **No container image maintenance**: No Dockerfile to update, no image builds to trigger
- **Faster startup**: No image pull latency
- **Latest tool versions**: Always uses latest Claude Code, uv, etc.
- **Simpler workflow**: Fewer permissions needed (`packages: read` not required)
- **No permission workarounds**: No temp directory fixes, no root user issues

### Container-less Disadvantages

- **Longer install time**: ~30s for tool installation each run
- **Network dependency**: Each run downloads tools
- **Version drift**: Tool versions may change between runs

### When to Use Each

**Use Container-less:**

- Simple tool requirements (Claude Code, uv, gh)
- When you want minimal maintenance
- When you always want latest tool versions

**Use Container:**

- Complex environment with many pre-installed tools
- When identical environment across runs is critical
- When you need tools not easily installable at runtime

## Workflows Using This Pattern

- `.github/workflows/tripwires-review.yml`
- `.github/workflows/dignified-python-review.yml`

## Troubleshooting

### Claude Code not found after installation

Ensure PATH is updated:

```yaml
echo "$HOME/.claude/local/bin" >> $GITHUB_PATH
```

### Permission denied errors

The `--dangerously-skip-permissions` flag requires non-root execution. On `ubuntu-latest`, this is the default.

### Tool installation failures

Add retries for network resilience:

```yaml
- name: Install Claude Code
  run: |
    for i in 1 2 3; do
      curl -fsSL https://claude.ai/install.sh | bash && break
      sleep 5
    done
    echo "$HOME/.claude/local/bin" >> $GITHUB_PATH
```

## Related Documentation

- [Claude Code in Docker CI](claude-code-docker.md) - Container-based approach

---
title: Container-less CI with Native Tool Installation
read_when:
  - Setting up Claude Code in GitHub Actions without containers
  - Comparing container vs container-less CI approaches
  - Choosing between container and container-less CI approaches
last_audited: "2026-02-05 20:38 PT"
audit_result: edited
---

# Container-less CI with Native Tool Installation

## Overview

This document covers the container-less approach for running Claude Code in GitHub Actions. For the container-based alternative, see [claude-code-docker.md](claude-code-docker.md).

**Pros:** No image maintenance, simpler workflow, no permission workarounds needed.

**Cons:** Network dependency on first run (binary is cached afterward), potential version drift.

## Implementation: Composite Actions

All erk workflows use composite actions to consolidate setup. There are two layers:

1. **`.github/actions/setup-claude-code/action.yml`** -- Downloads the Claude Code binary directly from GCS (bypassing the install script, which hangs in CI). Includes `actions/cache` so the binary is only downloaded on cache miss. Installs to `~/.local/bin/claude`.

2. **`.github/actions/erk-remote-setup/action.yml`** -- The full setup action used by most workflows. Calls `setup-claude-code`, installs uv (via `astral-sh/setup-uv@v5`), installs prettier, installs erk, validates Claude credentials, and configures git identity.

### Why Direct Download Instead of Install Script

The standard `curl -fsSL https://claude.ai/install.sh | bash` approach frequently hangs in CI environments. The `setup-claude-code` action documents the known issues and downloads the binary directly from the same GCS bucket the install script would use. See the comments in `.github/actions/setup-claude-code/action.yml` for issue links.

### Key Details

- **Claude Code PATH**: `~/.local/bin` (not `~/.claude/local/bin`)
- **`--dangerously-skip-permissions`**: Required for non-interactive CI execution. Works on `ubuntu-latest` because the runner executes as a non-root user (UID typically 1001).
- **erk install**: `uv tool install -e . --with-editable ./packages/erk-shared` (via `erk-remote-setup`) or `uv tool install --from . --with ./packages/erk-shared erk` (in simpler workflows like `code-reviews.yml`).

## Comparison: Container vs Container-less

| Aspect               | Container                                | Container-less            |
| -------------------- | ---------------------------------------- | ------------------------- |
| **Setup complexity** | High (Dockerfile, registry, credentials) | Low (composite actions)   |
| **Startup time**     | Variable (image pull)                    | Fast (binary cached)      |
| **Tool versions**    | Fixed at image build                     | Always latest stable      |
| **Maintenance**      | Image rebuilds required                  | Minimal                   |
| **Permissions**      | Complex (root user workarounds)          | Simple (runs as non-root) |
| **Consistency**      | High (identical environment)             | Medium (runner updates)   |
| **Package registry** | Required (GHCR auth)                     | Not required              |

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

All current erk CI workflows use the containerless pattern:

- `.github/workflows/code-reviews.yml` -- Uses `setup-claude-code` directly plus inline uv/erk steps (see [convention-based-reviews.md](convention-based-reviews.md))
- `.github/workflows/plan-implement.yml` -- Uses `erk-remote-setup` composite action
- `.github/workflows/pr-address.yml` -- Uses `erk-remote-setup` composite action
- `.github/workflows/pr-fix-conflicts.yml` -- Uses `erk-remote-setup` composite action
- `.github/workflows/learn.yml` -- Uses `erk-remote-setup` composite action

## Troubleshooting

### Claude Code not found after installation

Ensure PATH includes `~/.local/bin`. The `setup-claude-code` action handles this automatically. If installing manually, add `echo "$HOME/.local/bin" >> $GITHUB_PATH`.

### Permission denied errors

The `--dangerously-skip-permissions` flag requires non-root execution. On `ubuntu-latest`, this is the default.

### Install script hangs

Do not use `curl -fsSL https://claude.ai/install.sh | bash` in CI. Use the `setup-claude-code` composite action which downloads the binary directly from GCS with retries.

## Related Documentation

- [Claude Code in Docker CI](claude-code-docker.md) - Container-based approach

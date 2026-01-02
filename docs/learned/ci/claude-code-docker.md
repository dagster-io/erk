---
title: Claude Code in Docker CI
read_when:
  - Running Claude Code in GitHub Actions containers
  - Debugging permission errors in CI Docker containers
  - Using --dangerously-skip-permissions in CI
  - Setting up Claude Code for headless/automated execution
---

# Claude Code in Docker CI

## Overview

This document covers the specific requirements and gotchas for running Claude Code in Docker containers within GitHub Actions CI workflows.

## The Root User Restriction

Claude Code explicitly blocks `--dangerously-skip-permissions` when running as root (UID 0):

```
--dangerously-skip-permissions cannot be used with root/sudo privileges for security reasons
```

**This is intentional and has no override.** The check is `process.getuid() === 0` and exists as defense-in-depth—Claude Code cannot distinguish a properly isolated container from one with dangerous host mounts.

### Why This Matters for GitHub Actions

When a workflow uses a `container:` directive, GitHub Actions runs as root by default inside that container. Combined with `--dangerously-skip-permissions` (required for non-interactive tool execution), this triggers the security block.

## The Erk Solution

The `ghcr.io/dagster-io/erk-ci:latest` image includes:

1. **Non-root user** (`ci-user`, UID 1001) created during image build
2. **Passwordless sudo** for `ci-user` to handle operations requiring root
3. **Claude Code installed for ci-user** in `/home/ci-user/.local/bin`
4. **`USER ci-user` directive** making non-root the default

### Dockerfile Pattern

```dockerfile
# Create non-root user with sudo access
RUN useradd -m -u 1001 -s /bin/bash ci-user \
    && echo "ci-user ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/ci-user \
    && chmod 0440 /etc/sudoers.d/ci-user

# Install Claude Code for ci-user
USER ci-user
ENV PATH="/home/ci-user/.local/bin:${PATH}"
RUN curl -fsSL https://claude.ai/install.sh | bash

# Set default user
USER ci-user
```

## GitHub Actions Temp Directory Permissions

A secondary issue arises when running as non-root: GitHub Actions creates `/__w/_temp/` directories as root before the container starts. The `actions/checkout@v4` post-cleanup phase fails with:

```
Error: EACCES: permission denied, open '/__w/_temp/_runner_file_commands/save_state_...'
```

### Solution: Early Permission Fix

Add this step immediately after checkout in workflows using the container:

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    fetch-depth: 1

- name: Fix Actions temp directory permissions
  run: sudo chmod -R 777 /__w/_temp
```

This uses the passwordless sudo configured in the Dockerfile to grant write access to the temp directory.

## Claude Code CI Flags

Key flags for headless CI execution:

| Flag                             | Purpose                                                      |
| -------------------------------- | ------------------------------------------------------------ |
| `-p, --print`                    | Non-interactive mode; outputs result instead of launching UI |
| `--output-format stream-json`    | Streams JSONL for real-time parsing                          |
| `--max-turns N`                  | Caps agentic iterations to prevent runaway costs             |
| `--allowedTools "..."`           | Whitelist specific tools for auto-approval                   |
| `--dangerously-skip-permissions` | Skip all permission prompts (requires non-root)              |
| `--verbose`                      | Required with `--print` for stream-json output               |

### Tool Allowlisting

The `--allowedTools` flag provides granular control:

```bash
# Allow entire tools
--allowedTools "Read" "Edit" "Grep" "Glob"

# Bash with prefix-based pattern matching
--allowedTools "Bash(npm run test:*)"  # Any npm test command
--allowedTools "Bash(git commit:*)"    # Git commits with any message

# Path restrictions for file operations
--allowedTools "Write(src/**)"         # Write only in src/
```

**Important:** `--allowedTools` may be ignored with certain permission modes. Use targeted allowlists rather than broad bypasses.

## Affected Workflows

Workflows in this project using the Docker container:

- `.github/workflows/tripwires-review.yml`
- `.github/workflows/dignified-python-review.yml`

Both require:

1. The `ghcr.io/dagster-io/erk-ci:latest` image with ci-user
2. The temp directory permission fix step

## Alternative Approaches

### Official GitHub Action

For simpler cases without custom tooling:

```yaml
- uses: anthropics/claude-code-action@v1
  with:
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    claude_args: "--max-turns 10 --model claude-opus-4-5"
```

Runs on `ubuntu-latest` as non-root, avoiding the issue entirely.

### Runtime User Switching

If Dockerfile modifications aren't possible:

```yaml
- name: Setup non-root user and run Claude
  run: |
    useradd -u 1001 -m ci-user
    chown -R ci-user:ci-user $GITHUB_WORKSPACE
    su - ci-user -c "claude --dangerously-skip-permissions -p 'Task'"
```

## Related Issues

- PR #3837: Added `USER ci-user` to Dockerfile
- PR #3839: Added temp directory permission fix
- Claude Code issue #9184: Documents the root restriction
- Claude Code issue #12232: `--allowedTools` behavior with permission modes

## Community Resources

- [claude-code-root-runner](https://github.com/gagarinyury/claude-code-root-runner): Wrapper that creates temp users
- [claude-code-container](https://github.com/tintinweb/claude-code-container): Security-hardened container setup
- [claude-code-yolo](https://github.com/thevibeworks/claude-code-yolo): Docker wrapper with UID mapping

---
title: Docker Isolation Mode
read_when:
  - "running erk implement with --docker flag"
  - "building the erk-local Docker image"
  - "understanding Docker volume mounts for Claude Code"
---

# Docker Isolation Mode

## Overview

The `--docker` flag for `erk implement` and `erk prepare` runs Claude Code inside a Docker container, providing filesystem isolation. Claude can only access the mounted worktree, making `--dangerously-skip-permissions` safe to use.

**Use case**: Local development when you want agent isolation without a full remote environment.

**Contrast with CI Docker**: The CI image (`docs/learned/ci/claude-code-docker.md`) is for GitHub Actions. This local image is optimized for interactive TTY use.

## Usage

```bash
# Prepare with Docker flag (activation command includes --docker)
erk prepare 123 --docker

# Run implementation directly in Docker
erk implement --docker

# Use custom image
erk implement --docker --docker-image my-custom:latest
```

## How It Works

### Volume Mounts

| Host Path    | Container Path          | Mode | Purpose                                  |
| ------------ | ----------------------- | ---- | ---------------------------------------- |
| `<worktree>` | `/workspace`            | rw   | Working directory (only accessible path) |
| `~/.claude/` | `/home/ci-user/.claude` | rw   | Auth preservation                        |
| `~/.ssh/`    | `/home/ci-user/.ssh`    | ro   | Git push operations                      |

### UID/GID Mapping

Docker runs with `--user $(id -u):$(id -g)` to match host file ownership:

```python
# From docker_executor.py
uid = os.getuid()
gid = os.getgid()
args.extend(["--user", f"{uid}:{gid}"])
```

This ensures files created by Claude inside the container are owned by the host user.

## The Local Development Image

**Location**: `.erk/docker/Dockerfile`

**Build command**: `docker build -t erk-local -f .erk/docker/Dockerfile .`

**Image contents**:

- Ubuntu 22.04 base
- Python 3.11 (via uv)
- Node.js 20
- Claude Code CLI
- prettier, graphite-cli
- Non-root `ci-user` (UID 1001) with passwordless sudo

**Auto-build**: If `erk-local:latest` doesn't exist, `erk implement --docker` builds it automatically.

## Activation Modes

The activation system (see [activation-scripts.md](activation-scripts.md)) includes Docker-specific modes:

| Mode                         | Command Shown                                         |
| ---------------------------- | ----------------------------------------------------- |
| `implement_docker`           | `source <path> && erk implement --docker`             |
| `implement_docker_dangerous` | `source <path> && erk implement --docker --dangerous` |

**Source**: `src/erk/cli/activation.py` (ActivationMode Literal type)

## Key Differences from CI Docker

| Aspect   | Local (`--docker`)         | CI (`claude-code-docker.md`) |
| -------- | -------------------------- | ---------------------------- |
| Use case | Interactive local dev      | GitHub Actions               |
| Image    | `.erk/docker/Dockerfile`   | `.github/docker/Dockerfile`  |
| User     | Host UID via `--user` flag | Fixed `ci-user`              |
| Mode     | Interactive TTY (`-it`)    | Headless (`--print`)         |
| Mounts   | Worktree + auth dirs       | Workspace only               |

## Implementation Details

**Source files**:

- `src/erk/cli/commands/docker_executor.py` - Core execution logic
- `src/erk/cli/commands/implement.py` - `--docker` flag handling
- `src/erk/cli/commands/prepare.py` - `--docker` passthrough

**Key functions**:

- `build_docker_run_args()` - Constructs `docker run` arguments
- `build_claude_command_args()` - Constructs Claude CLI arguments
- `execute_docker_interactive()` - Replaces process with `docker run`
- `execute_docker_non_interactive()` - Runs commands via subprocess

## Related Documentation

- [Claude Code in Docker CI](../ci/claude-code-docker.md) - CI/GitHub Actions use case
- [Activation Scripts](activation-scripts.md) - Shell activation system

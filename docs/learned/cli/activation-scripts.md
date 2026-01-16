---
title: Activation Scripts
read_when:
  - "working with worktree environment setup"
  - "understanding .erk/activate.sh scripts"
  - "configuring post-create commands"
---

# Activation Scripts

## Overview

Erk generates `.erk/activate.sh` scripts in worktrees to provide a shell-sourceable environment setup. This enables opt-in shell integration where users explicitly source the script rather than relying on automatic shell manipulation.

## What the Script Does

When sourced, `.erk/activate.sh`:

1. CDs to the worktree directory
2. Creates `.venv` with `uv sync` if not present
3. Sources `.venv/bin/activate` if present
4. Loads `.env` file (using `set -a` for allexport)
5. Runs configured post-create commands
6. Displays activation confirmation

## Key Functions

| Function                            | Purpose                                                |
| ----------------------------------- | ------------------------------------------------------ |
| `render_activation_script()`        | Generates script content (used for navigation too)     |
| `write_worktree_activate_script()`  | Writes `.erk/activate.sh`, creates directory if needed |
| `ensure_worktree_activate_script()` | Idempotent version (create only if missing)            |

**Source:** `src/erk/cli/activation.py`

## When Scripts Are Generated

Scripts are generated during worktree creation:

- `erk wt create` - writes script after creating worktree
- `run_post_worktree_setup()` - shared function for all worktree creation paths

## Configuration

Post-create commands from `.erk/config.toml` are embedded in the script:

```toml
[post_create]
shell = "bash"
commands = [
  "uv run make dev_install",
]
```

## Transparency Logging

Scripts include `__erk_log()` helpers respecting:

- `ERK_QUIET=1` - Suppresses output
- `ERK_VERBOSE=1` - Shows detailed paths

## Related Topics

- [Shell Integration Architecture](../architecture/shell-integration-architecture.md) - Full shell integration design
- [Template Variables](template-variables.md) - .env template substitution

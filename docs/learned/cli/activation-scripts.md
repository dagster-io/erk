---
title: Activation Scripts
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
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

## Post-CD Commands

Activation scripts support dynamic post-CD commands via the `post_cd_commands` parameter in `render_activation_script()`. These commands are appended after the `cd` line and execute in the target worktree directory.

**Example:** PR checkout with `--sync` flag passes `["gt submit --no-interactive"]` as `post_cd_commands`, causing the branch to be submitted to Graphite after navigation.

**Implementation:** `src/erk/cli/commands/pr/checkout_cmd.py` uses the `post_cd_commands` parameter when `should_track_with_graphite and sync` evaluates to True.

## Related Topics

- [Template Variables](template-variables.md) - .env template substitution
- [Shell Activation Pattern](shell-activation-pattern.md) - Source pattern for navigation

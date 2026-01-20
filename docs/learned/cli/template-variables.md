---
title: Template Variables Reference
read_when:
  - "configuring .env templates"
  - "using substitution variables in config.toml"
  - "setting environment variables per worktree"
  - "updating environment when switching worktrees"
---

# Template Variables Reference

## Overview

Template variables can be used in `config.toml` env sections. They are substituted when `.env` files are generated during worktree creation.

## Available Variables

| Variable          | Description                          | Example Value                     |
| ----------------- | ------------------------------------ | --------------------------------- |
| `{worktree_path}` | Absolute path to worktree directory  | `/Users/you/erks/repo/my-feature` |
| `{repo_root}`     | Absolute path to git repository root | `/Users/you/code/repo`            |
| `{name}`          | Worktree name                        | `my-feature`                      |

## Auto-Generated Environment Variables

These are always added to `.env` regardless of config:

| Variable        | Source            |
| --------------- | ----------------- |
| `WORKTREE_PATH` | `{worktree_path}` |
| `REPO_ROOT`     | `{repo_root}`     |
| `WORKTREE_NAME` | `{name}`          |

## Example Configuration

**Repo-level** (`.erk/config.toml`):

```toml
[env]
DAGSTER_GIT_REPO_DIR = "{worktree_path}"
DATABASE_URL = "postgresql://localhost/{name}"
```

## Generated .env

When creating a worktree:

```bash
DAGSTER_GIT_REPO_DIR="/Users/you/erks/repo/my-feature"
DATABASE_URL="postgresql://localhost/my-feature"
WORKTREE_PATH="/Users/you/erks/repo/my-feature"
REPO_ROOT="/Users/you/code/repo"
WORKTREE_NAME="my-feature"
```

**File**: `src/erk/cli/commands/wt/create_cmd.py` (see `make_env_content()`)

## When Environment Variables Are Loaded

Environment variables are loaded in two phases:

1. **Worktree creation**: Erk generates `.env` with substituted template values
2. **Worktree activation**: The activation script sources `.env` using `set -a` (allexport mode)

The relevant shell snippet from `activate.sh`:

```bash
# Load .env into the environment (allexport)
set -a
if [ -f ./.env ]; then
  . ./.env
fi
set +a
```

This means environment variables are automatically updated when you switch worktrees via `erk wt checkout` or shell integration.

## Common Use Cases

| Variable               | Purpose                   | Example Value                   |
| ---------------------- | ------------------------- | ------------------------------- |
| `DAGSTER_GIT_REPO_DIR` | Point Dagster to worktree | `{worktree_path}`               |
| `DATABASE_URL`         | Per-worktree database     | `postgresql://localhost/{name}` |
| `LOG_FILE`             | Separate log files        | `{worktree_path}/logs/app.log`  |
| `CONFIG_PATH`          | Worktree-specific config  | `{worktree_path}/.local-config` |

## Related Topics

- [Worktree Metadata](../architecture/worktree-metadata.md) - Per-worktree storage
- [Configuration Layers](../configuration/config-layers.md) - How repo and local configs merge

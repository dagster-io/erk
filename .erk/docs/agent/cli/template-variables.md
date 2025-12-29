---
title: Template Variables Reference
read_when:
  - "configuring .env templates"
  - "using substitution variables in config.toml"
---

# Template Variables Reference

## Overview

Template variables can be used in `config.toml` env sections. They are substituted when `.env` files are generated during worktree creation.

## Available Variables

| Variable          | Description                         | Example Value                     |
| ----------------- | ----------------------------------- | --------------------------------- |
| `{worktree_path}` | Absolute path to worktree directory | `/Users/you/erks/repo/my-feature` |
| `{repo_root}`     | Absolute path to git repository     | `/Users/you/code/repo`            |
| `{name}`          | Worktree name                       | `my-feature`                      |

## Auto-Generated Environment Variables

These are always added to `.env` regardless of config:

| Variable        | Source            |
| --------------- | ----------------- |
| `WORKTREE_PATH` | `{worktree_path}` |
| `REPO_ROOT`     | `{repo_root}`     |
| `WORKTREE_NAME` | `{name}`          |

## Example Configuration

**Repo-level** (`~/.erk/repos/my-repo/config.toml`):

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

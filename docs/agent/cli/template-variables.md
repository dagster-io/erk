---
title: Template Variables Reference
read_when:
  - "configuring .env templates"
  - "using substitution variables in config.toml"
  - "writing project.toml configuration"
---

# Template Variables Reference

## Overview

Template variables can be used in `config.toml` and `project.toml` env sections. They are substituted when `.env` files are generated during worktree creation.

## Available Variables

| Variable          | Description                                     | Example Value                                        |
| ----------------- | ----------------------------------------------- | ---------------------------------------------------- |
| `{worktree_path}` | Absolute path to worktree directory             | `/Users/you/erks/repo/my-feature`                    |
| `{repo_root}`     | Absolute path to git repository root            | `/Users/you/code/repo`                               |
| `{name}`          | Worktree name                                   | `my-feature`                                         |
| `{project_root}`  | Absolute path to project directory (if in proj) | `/Users/you/erks/repo/my-feature/python_modules/dop` |
| `{project_name}`  | Project name (if in project)                    | `dop`                                                |

## Auto-Generated Environment Variables

These are always added to `.env` regardless of config:

| Variable        | Source                                |
| --------------- | ------------------------------------- |
| `WORKTREE_PATH` | `{worktree_path}`                     |
| `REPO_ROOT`     | `{repo_root}`                         |
| `WORKTREE_NAME` | `{name}`                              |
| `PROJECT_ROOT`  | `{project_root}` (only if in project) |
| `PROJECT_NAME`  | `{project_name}` (only if in project) |

## Example Configuration

**Repo-level** (`~/.erk/repos/my-repo/config.toml`):

```toml
[env]
DAGSTER_GIT_REPO_DIR = "{worktree_path}"
DATABASE_URL = "postgresql://localhost/{name}"
```

**Project-level** (`repo/python_modules/dop/.erk/project.toml`):

```toml
[env]
DAGSTER_HOME = "{project_root}"
PROJECT_CONFIG = "{project_root}/config.yaml"
```

## Generated .env

When creating a worktree from the project directory:

```bash
DAGSTER_GIT_REPO_DIR="/Users/you/erks/repo/my-feature"
DATABASE_URL="postgresql://localhost/my-feature"
DAGSTER_HOME="/Users/you/erks/repo/my-feature/python_modules/dop"
PROJECT_CONFIG="/Users/you/erks/repo/my-feature/python_modules/dop/config.yaml"
WORKTREE_PATH="/Users/you/erks/repo/my-feature"
REPO_ROOT="/Users/you/code/repo"
WORKTREE_NAME="my-feature"
PROJECT_ROOT="/Users/you/erks/repo/my-feature/python_modules/dop"
PROJECT_NAME="dop"
```

**File**: `src/erk/cli/commands/wt/create_cmd.py` (see `make_env_content()`)

## Related Topics

- [Glossary: Project Config](../glossary.md#project-config) - Config merge semantics
- [Worktree Metadata](../architecture/worktree-metadata.md) - Per-worktree storage

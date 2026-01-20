# Configuration Reference

Erk uses a layered configuration system with global, repository, and local configuration files.

## Configuration Files

| File                     | Scope            | Versioned | Purpose                         |
| ------------------------ | ---------------- | --------- | ------------------------------- |
| `~/.erk/config.toml`     | All repositories | No        | User-wide settings              |
| `.erk/config.toml`       | Single repo      | Yes       | Team-shared repository settings |
| `.erk/config.local.toml` | Single repo      | No        | Personal overrides (gitignored) |

## Global Configuration

Settings in `~/.erk/config.toml` apply to all repositories.

| Option              | Type    | Description                                     |
| ------------------- | ------- | ----------------------------------------------- |
| `erks_root`         | string  | Directory where worktrees are stored            |
| `use_graphite`      | boolean | Enable Graphite integration for stacked PRs     |
| `github_planning`   | boolean | Enable GitHub issue-based planning              |
| `shell_integration` | boolean | Enable auto-navigation when switching worktrees |

**Example:**

```toml
erks_root = "/Users/you/erks"
use_graphite = true
github_planning = true
shell_integration = true
```

## Repository Configuration

Settings in `.erk/config.toml` are shared across the team and checked into git.

### `[env]` - Environment Variables

Define environment variables that are templated into each worktree's `.env` file.

```toml
[env]
DAGSTER_GIT_REPO_DIR = "{worktree_path}"
DATABASE_URL = "postgresql://localhost/{name}"
MY_API_KEY = "shared-dev-key"
```

See [Environment Variables](#environment-variables) below for template syntax and loading behavior.

### `[post_create]` - Post-Creation Commands

Commands run after worktree creation.

```toml
[post_create]
shell = "bash"
commands = [
    "uv sync",
    "npm install"
]
```

### `[pool]` - Worktree Pool Settings

Configure the worktree pool for efficient worktree reuse.

```toml
[pool]
max_slots = 8

[pool.checkout]
shell = "bash"
commands = ["uv sync"]
```

## Environment Variables

Erk automatically manages environment variables per worktree, making it easy to configure tools that need worktree-specific paths.

### Template Variables

Use these placeholders in `[env]` values:

| Variable          | Description                          | Example Value                     |
| ----------------- | ------------------------------------ | --------------------------------- |
| `{worktree_path}` | Absolute path to worktree directory  | `/Users/you/erks/repo/my-feature` |
| `{repo_root}`     | Absolute path to git repository root | `/Users/you/code/repo`            |
| `{name}`          | Worktree name (branch slug)          | `my-feature`                      |

### Auto-Generated Variables

These variables are always added to `.env`, regardless of your configuration:

| Variable        | Source            | Description                 |
| --------------- | ----------------- | --------------------------- |
| `WORKTREE_PATH` | `{worktree_path}` | Current worktree path       |
| `REPO_ROOT`     | `{repo_root}`     | Repository root path        |
| `WORKTREE_NAME` | `{name}`          | Worktree name (branch slug) |

### When Variables Are Loaded

1. **Worktree creation**: Erk generates `.env` with substituted template values
2. **Worktree activation**: The activation script sources `.env` using `set -a` (allexport mode)

The activation script loads environment variables like this:

```bash
# Load .env into the environment (allexport)
set -a
if [ -f ./.env ]; then
  . ./.env
fi
set +a
```

### Example

**Configuration** (`.erk/config.toml`):

```toml
[env]
DAGSTER_GIT_REPO_DIR = "{worktree_path}"
DATABASE_URL = "postgresql://localhost/{name}"
```

**Generated `.env`** (for worktree `my-feature`):

```bash
DAGSTER_GIT_REPO_DIR="/Users/you/erks/repo/my-feature"
DATABASE_URL="postgresql://localhost/my-feature"
WORKTREE_PATH="/Users/you/erks/repo/my-feature"
REPO_ROOT="/Users/you/code/repo"
WORKTREE_NAME="my-feature"
```

### Common Use Cases

| Variable               | Purpose                         | Example Config                         |
| ---------------------- | ------------------------------- | -------------------------------------- |
| `DAGSTER_GIT_REPO_DIR` | Point Dagster to worktree       | `"{worktree_path}"`                    |
| `DATABASE_URL`         | Per-worktree database           | `"postgresql://localhost/{name}"`      |
| `LOG_FILE`             | Separate log files per worktree | `"{worktree_path}/logs/app.log"`       |
| `CONFIG_PATH`          | Worktree-specific config        | `"{worktree_path}/.local-config.json"` |

## See Also

- [Installation](../tutorials/installation.md) - Initial configuration
- [File Location Reference](file-locations.md) - Where config files live

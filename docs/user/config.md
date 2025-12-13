# Configuration Reference

Erk uses TOML configuration files at different scopes to control its behavior. This document describes all available configuration options.

## Configuration File Locations

Erk uses three levels of configuration:

- **Global config**: `~/.erk/config.toml` - User-wide settings
- **Repo config**: `.erk/config.toml` - Repository-specific settings
- **Project config**: `.erk/project.toml` - Project-specific settings (for monorepos)

## Global Configuration Options

Global configuration is stored in `~/.erk/config.toml` and affects all erk repositories for your user.

### `erk_root`

- **Type**: Path (string)
- **Default**: Set during `erk init`
- **Description**: Root directory where erk stores its metadata and worktrees

This is set automatically when you run `erk init` and typically should not be changed manually.

**Example**:
```toml
erk_root = "/home/user/erk-worktrees"
```

### `use_graphite`

- **Type**: Boolean
- **Default**: Auto-detected based on presence of `.git/_graphite/` directory
- **Description**: Enable Graphite integration for stacked PRs

When enabled, erk will use Graphite commands (`gt`) for branch management and PR submission. When disabled, erk uses standard git workflows.

**When to change**: Set to `true` if you use Graphite but erk doesn't auto-detect it, or set to `false` to force standard git workflows even if Graphite is installed.

**Example**:
```toml
use_graphite = true
```

### `show_pr_info`

- **Type**: Boolean
- **Default**: `true`
- **Description**: Show pull request information in worktree listings

When enabled, commands like `erk wt ls` will display PR status, PR numbers, and review state for each worktree's branch.

**When to change**: Set to `false` if you don't use GitHub PRs or want faster worktree listings (showing PR info requires API calls).

**Example**:
```toml
show_pr_info = false
```

### `github_planning`

- **Type**: Boolean
- **Default**: `true`
- **Description**: Enable GitHub integration for planning workflows

When enabled, erk plan commands will interact with GitHub issues for tracking implementation plans.

**When to change**: Set to `false` if you don't want plan commands to interact with GitHub, or if you're working in a repository without GitHub issues enabled.

**Example**:
```toml
github_planning = false
```

### `auto_restack_skip_dangerous`

- **Type**: Boolean
- **Default**: `false`
- **Description**: Skip the `--dangerous` flag when running auto-restack operations

When `true`, auto-restack commands will be more conservative and skip operations that could be risky. When `false`, auto-restack will include the `--dangerous` flag for more aggressive restacking.

**When to change**: Set to `true` if you want safer (but potentially less effective) auto-restack behavior.

**Example**:
```toml
auto_restack_skip_dangerous = true
```

### `shell_setup_complete`

- **Type**: Boolean
- **Default**: `false`
- **Description**: Internal flag tracking whether shell integration has been configured

This is set automatically by `erk shell-setup` and typically should not be changed manually. It tracks whether your shell has been configured with erk's completion and helper functions.

**Example**:
```toml
shell_setup_complete = true
```

## Repository Configuration Options

Repository configuration is stored in `.erk/config.toml` at the repository root and affects all worktrees in that repository.

### `trunk-branch`

- **Type**: String
- **Default**: Auto-detected (`main` or `master`)
- **Description**: The name of the trunk/main branch for the repository

This is typically detected automatically during `erk init`. Change this if your repository uses a non-standard trunk branch name.

**When to change**: If your repository uses a trunk branch other than `main` or `master` (e.g., `develop`, `trunk`).

**Example**:
```toml
trunk-branch = "develop"
```

## Project Configuration Options

Project configuration is stored in `.erk/project.toml` and is used for monorepo setups where different subdirectories have different build/test workflows.

### `env`

- **Type**: Table (key-value pairs)
- **Default**: Empty
- **Description**: Environment variables to set when working in this project

These environment variables will be available to post-create commands and can be used to configure project-specific tools.

**Example**:
```toml
[env]
NODE_ENV = "development"
DATABASE_URL = "postgresql://localhost/myapp"
```

### `post_create.shell`

- **Type**: String
- **Default**: System default shell
- **Description**: Shell to use for running post-create commands

**When to change**: Specify if your post-create commands require a specific shell (e.g., `bash` for bash-specific syntax).

**Example**:
```toml
[post_create]
shell = "bash"
```

### `post_create.commands`

- **Type**: Array of strings
- **Default**: Empty
- **Description**: Commands to run automatically after creating a new worktree

These commands run in the new worktree directory after it's created. Useful for installing dependencies, setting up databases, or other initialization tasks.

**When to change**: Add commands that should run whenever you create a new worktree for this project.

**Example**:
```toml
[post_create]
commands = [
    "npm install",
    "npm run db:migrate"
]
```

## Configuration Precedence

When multiple configuration levels define the same setting:

1. Project config (`.erk/project.toml`) - highest priority
2. Repo config (`.erk/config.toml`)
3. Global config (`~/.erk/config.toml`)
4. Built-in defaults - lowest priority

## Editing Configuration

You can edit configuration files directly with any text editor, or use erk commands:

```bash
# Edit global config
erk config edit

# Edit repo config
erk config edit --repo

# View current configuration
erk config show
```

## Configuration Examples

### Minimal global config for Graphite user

```toml
erk_root = "/home/user/erk-worktrees"
use_graphite = true
show_pr_info = true
```

### Non-Graphite user who prefers standard git

```toml
erk_root = "/home/user/erk-worktrees"
use_graphite = false
show_pr_info = true
```

### Monorepo with frontend project

```toml
# .erk/project.toml in frontend/ directory
[env]
NODE_ENV = "development"

[post_create]
shell = "bash"
commands = [
    "npm install",
    "npm run build"
]
```

---
title: Configuration Layers
read_when:
  - "understanding the configuration system"
  - "deciding where to put a configuration setting"
  - "debugging why a config value isn't taking effect"
  - "working with LoadedConfig or merge_configs"
---

# Configuration Layers

Erk uses a layered configuration system where settings are merged from multiple sources.

## Overview

| Layer  | Location             | Scope       | Versioned | Merge Order |
| ------ | -------------------- | ----------- | --------- | ----------- |
| Global | `~/.erk/config.toml` | All repos   | No        | N/A         |
| Repo   | `.erk/config.toml`   | All users   | Yes       | 1st         |
| Local  | `.erk/local.toml`    | Single user | No        | 2nd         |

## Layer Details

### Global Config (`~/.erk/config.toml`)

User-wide settings that apply across all repositories.

**Contains:**

- `erks_root` - Where worktrees are stored
- `use_graphite` - Enable/disable Graphite integration
- `shell_setup_complete` - Whether shell integration is configured
- `github_planning` - Enable GitHub-based planning
- `prompt_learn_on_land` - Prompt for learning extraction on PR land

**Not merged with other configs** - this is handled separately via `GlobalConfig`.

### Repo Config (`.erk/config.toml`)

Team-shared settings for the repository. Checked into git.

**Contains:**

- `[env]` - Environment variables for worktrees
- `[post_create]` - Commands to run after worktree creation
- `[pool]` - Worktree pool settings (max_slots)
- `[pool.checkout]` - Commands to run on pool checkout
- `[plans]` - Plan issue repository settings

### Local Config (`.erk/local.toml`)

Per-user overrides. Gitignored to prevent committing personal settings.

**Use cases:**

- User needs more/fewer worktree slots than team default
- User prefers different shell or activation commands
- User has personal environment variables

## Merge Semantics

When a repo has both `.erk/config.toml` and `.erk/local.toml`, they are merged:

| Field                    | Merge Behavior                         |
| ------------------------ | -------------------------------------- |
| `env`                    | Dict merge (local overrides repo)      |
| `post_create.commands`   | Concatenation (repo first, then local) |
| `post_create.shell`      | Override (local wins if set)           |
| `pool.max_slots`         | Override (local wins if set)           |
| `pool.checkout.commands` | Concatenation (repo first, then local) |
| `pool.checkout.shell`    | Override (local wins if set)           |
| `plans.repo`             | Override (local wins if set)           |

### Example

**Repo config (`.erk/config.toml`):**

```toml
[env]
TEAM_VAR = "shared"

[post_create]
shell = "bash"
commands = ["uv sync"]

[pool]
max_slots = 4
```

**Local config (`.erk/local.toml`):**

```toml
[env]
MY_VAR = "personal"

[post_create]
commands = ["source ~/.zshrc"]

[pool]
max_slots = 8
```

**Merged result:**

```toml
[env]
TEAM_VAR = "shared"   # from repo
MY_VAR = "personal"   # from local

[post_create]
shell = "bash"        # from repo (local didn't override)
commands = ["uv sync", "source ~/.zshrc"]  # concatenated

[pool]
max_slots = 8         # local override
```

## Code References

- **Loading**: `load_config()` and `load_local_config()` in `src/erk/cli/config.py`
- **Merging**: `merge_configs_with_local()` in `src/erk/cli/config.py`
- **Context creation**: `create_context()` in `src/erk/core/context.py`
- **Result**: `ErkContext.local_config` field contains the merged config

## Decision Guide

**Where should I put this setting?**

| If the setting is...              | Put it in...         |
| --------------------------------- | -------------------- |
| Shared by all team members        | `.erk/config.toml`   |
| Personal preference for this repo | `.erk/local.toml`    |
| Applies to all your repos         | `~/.erk/config.toml` |

# Per-Repo Codespace Configuration

## Context

When running `erk codespace connect` from different repos (e.g., dagster-compass vs erk), users must either pass `--codespace NAME` every time or manually switch the global default. There's no way to associate a codespace (or remote working directory) with a specific repository.

This change adds a `[codespace]` section to `.erk/config.toml` / `.erk/config.local.toml` so codespace resolution is repo-aware.

## Config Shape

```toml
# In .erk/config.local.toml (user-specific, gitignored)
[codespace]
name = "my-compass-codespace"                    # maps to ~/.erk/codespaces.toml entry
working_directory = "/workspaces/dagster-compass" # cd here on remote before running commands
```

## Resolution Precedence

1. Explicit CLI `NAME` argument (highest)
2. `codespace.name` from repo config (local overrides shared)
3. Global `default_codespace` from `~/.erk/codespaces.toml` (lowest)

`working_directory` is always applied regardless of how the codespace was resolved (even with explicit CLI name).

## Implementation Steps

### Step 1: Add fields to `LoadedConfig`

**File**: `packages/erk-shared/src/erk_shared/context/types.py`

Add `codespace_name: str | None` and `codespace_working_directory: str | None` to the `LoadedConfig` dataclass and its `test()` factory.

### Step 2: Parse `[codespace]` section in config

**File**: `src/erk/cli/config.py`

- In `_parse_config_file()`: parse `[codespace]` section (same pattern as `[docs]`/`[plans]`)
- In `load_config()` and `load_local_config()` default returns: add `codespace_name=None, codespace_working_directory=None`
- In `merge_configs()`: pass through repo-level codespace fields
- In `merge_configs_with_local()`: local overrides base if set

### Step 3: Update `resolve_codespace()`

**File**: `src/erk/cli/commands/codespace/resolve.py`

Add `config_codespace_name: str | None = None` kwarg. Insert a new tier between CLI name and global default:

```python
# 2. Repo config codespace name
if config_codespace_name is not None:
    codespace = registry.get(config_codespace_name)
    if codespace is None:
        # Error: repo config references unregistered codespace
```

### Step 4: Update `build_codespace_ssh_command()`

**File**: `src/erk/core/codespace_run.py`

Add `working_directory: str | None = None` kwarg. Prepend `cd <quoted_dir> &&` when set.

### Step 5: Update `connect_cmd.py`

**File**: `src/erk/cli/commands/codespace/connect_cmd.py`

- Pass `config_codespace_name=ctx.local_config.codespace_name` to resolver
- Prepend `cd <dir> &&` from `ctx.local_config.codespace_working_directory` before setup commands

### Step 6: Update `run/objective/plan_cmd.py`

**File**: `src/erk/cli/commands/codespace/run/objective/plan_cmd.py`

- Pass `config_codespace_name=ctx.local_config.codespace_name` to resolver
- Pass `working_directory=ctx.local_config.codespace_working_directory` to `build_codespace_ssh_command()`

### Step 7: Tests

- **Config parsing**: Parse `[codespace]` name/working_directory, defaults to None
- **Config merging**: Local overrides base codespace fields
- **resolve_codespace**: Config name used when no CLI name; CLI overrides config; config overrides global default; error when config name not registered
- **connect_cmd**: Working directory prepended as `cd`; repo config codespace name used
- **build_codespace_ssh_command**: Working directory injection, quoting
- **run plan_cmd**: Config name and working directory threaded through

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/context/types.py` | Add 2 fields to `LoadedConfig` |
| `src/erk/cli/config.py` | Parse `[codespace]`, merge, defaults |
| `src/erk/cli/commands/codespace/resolve.py` | 3-tier resolution |
| `src/erk/cli/commands/codespace/connect_cmd.py` | Thread config to resolver + working_directory |
| `src/erk/cli/commands/codespace/run/objective/plan_cmd.py` | Thread config to resolver + working_directory |
| `src/erk/core/codespace_run.py` | Accept working_directory param |

## Files NOT Modified

- `CodespaceRegistry` ABC / real / fake — repo config is a separate layer
- `ErkContext` — already carries `local_config: LoadedConfig`
- `context.py` factory functions — new fields flow through existing parsing/merging

## Verification

1. Add `[codespace] name = "test"` to a repo's `.erk/config.local.toml`
2. Register a codespace with that name via `erk codespace setup`
3. Run `erk codespace connect` from within that repo — should connect to the configured codespace
4. Run `erk codespace connect other-name` — CLI arg should override config
5. Run tests: `pytest tests/unit/cli/commands/codespace/ tests/unit/cli/test_config*.py tests/unit/core/codespace/`

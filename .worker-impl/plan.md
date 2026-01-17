# Fix --local Config Semantics: Repo-Local Instead of Worktree-Local

## Problem

When running `erk config set --local pool.max_slots 64` from the main worktree, the setting is not visible in secondary worktrees. The `--local` semantics should be **repo-local** (shared across all worktrees in a repository), not worktree-local.

## Root Cause

The bug is that config loading and writing uses `repo.root` (the worktree working directory) instead of `repo.main_repo_root` (the main repository root).

**Current behavior:**
- Main worktree: `repo.root` = `/Users/schrockn/code/erk/`
- Secondary worktree: `repo.root` = `/Users/schrockn/code/erk/.worktrees/P5086-xxx/`

Config files are stored at `<repo.root>/.erk/config.local.toml`, so each worktree looks in a different location.

**Expected behavior:**
All worktrees should load/write config from the main repo's `.erk/` directory at `<repo.main_repo_root>/.erk/config.local.toml`.

## Files to Modify

### 1. `src/erk/core/context.py` (lines 516-518)

Change config loading to use `main_repo_root`:

```python
# Before:
repo_config = load_config(repo.root)
user_local_config = load_local_config(repo.root)

# After:
main_root = repo.main_repo_root or repo.root
repo_config = load_config(main_root)
user_local_config = load_local_config(main_root)
```

### 2. `src/erk/cli/commands/config.py` (lines 429 and 503)

Change config writing to use `main_repo_root`:

**Line 429** (overridable global keys):
```python
# Before:
_write_to_repo_config(repo_root=repo.root, key=key, value=parsed_bool, local=local)

# After:
_write_to_repo_config(repo_root=repo.main_repo_root or repo.root, key=key, value=parsed_bool, local=local)
```

**Line 503** (repo config keys):
```python
# Before:
_write_to_repo_config(repo_root=repo.root, key=key, value=transformed, local=local)

# After:
_write_to_repo_config(repo_root=repo.main_repo_root or repo.root, key=key, value=transformed, local=local)
```

## Test Plan

### New Test: `tests/commands/setup/test_config_worktree.py`

Add a test that verifies config set in the main worktree is readable from a secondary worktree:

```python
def test_local_config_shared_across_worktrees() -> None:
    """Config set with --local in main repo is visible in secondary worktrees."""
    # Setup:
    # - Create main repo with .erk/ directory
    # - Create worktree pointing to secondary location
    # - RepoContext for secondary worktree has main_repo_root pointing to main repo

    # Act: Load config from secondary worktree context

    # Assert: Config from main repo's .erk/config.local.toml is loaded
```

### Verification

1. Run existing config tests: `uv run pytest tests/commands/setup/test_config.py`
2. Run new worktree config test
3. Manual verification:
   ```bash
   # In main worktree
   erk config set --local pool.max_slots 64

   # In secondary worktree
   erk config get pool.max_slots  # Should return 64
   ```

## Related Documentation

- `docs/learned/configuration/config-layers.md` - Config layer architecture
- `fake-driven-testing` skill - Test patterns for this change
# Move `uv sync` outside VIRTUAL_ENV guard in activation scripts

## Context

When a worktree slot is reused for a new branch (via `erk br co --new-slot --for-plan`), the user hits `ModuleNotFoundError` for newly added packages (e.g., `anthropic`). This happens because:

1. `allocate_slot_for_branch` checks out the new branch (updating `uv.lock` on disk)
2. The user sources the activation script, which `cd`s into the worktree
3. direnv triggers and loads `.erk/bin/activate.sh`
4. The VIRTUAL_ENV guard (`if [ "$VIRTUAL_ENV" != ".../.venv" ]`) may **skip** `uv sync` if VIRTUAL_ENV is already set from a prior session or direnv state
5. `erk completion zsh` (inside the guard) and then `erk implement` both fail because new deps weren't installed

The root cause: `uv sync` is inside the VIRTUAL_ENV guard, so it gets skipped when the guard determines the venv is "already active" — even though the branch (and lockfile) changed.

## Changes

### 1. Move `uv sync` outside the VIRTUAL_ENV guard

**File**: `src/erk/cli/activation.py` — `render_activation_script()`

Restructure the generated shell script so `uv sync` and `uv pip install --no-deps` run **unconditionally** (before the guard), while venv activation, `.env` loading, and shell completion remain guarded:

```
cd {worktree_path}

# Always sync deps (idempotent — handles branch switches in reused slots)
if [ ! -d {venv_dir} ]; then
  __erk_log "->" "Creating virtual environment..."
fi
uv sync --quiet
uv pip install --no-deps --quiet -e . -e packages/erk-shared -e packages/erk-statusline

# Skip activation if VIRTUAL_ENV already points to this worktree's .venv
if [ "$VIRTUAL_ENV" != ".../.venv" ]; then
  unset VIRTUAL_ENV
  source .venv/bin/activate
  load .env
  erk completion
fi
{post_cd_commands}
{final_message}
```

`uv sync` is idempotent and fast (~10ms no-op when deps are up to date). Running it unconditionally ensures new packages are installed after branch switches.

### 2. Always regenerate `.erk/bin/activate.sh` on slot allocation

**File**: `src/erk/cli/commands/slot/common.py` — `allocate_slot_for_branch()`

Change line 701 from `ensure_worktree_activate_script` to `write_worktree_activate_script`. The `ensure_` variant skips regeneration if the file exists, which means old slots keep stale activation scripts. Always regenerating ensures the latest template (with `uv sync` outside the guard) is used.

### 3. Update tests

**File**: `tests/unit/cli/test_activation.py`

- Update `test_render_activation_script_contains_virtual_env_guard` — `uv sync` and `uv pip install` should now be **outside** the guard
- Update `test_render_activation_script_guard_with_post_cd_commands` — guard position assertions may shift
- Existing tests for `uv sync` presence and ordering (`test_render_activation_script_refreshes_workspace_packages`) should still pass

## Verification

1. Run activation script tests: `uv run pytest tests/unit/cli/test_activation.py`
2. Run slot allocation tests: search for tests of `allocate_slot_for_branch` and run those
3. Generate an activation script and visually confirm `uv sync` appears before the `if [ "$VIRTUAL_ENV"` guard

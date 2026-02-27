# Improve erk upgrade tools

## Context

After upgrading erk to v0.9.0, `erk doctor` reported 4 error categories that required an AI agent to diagnose and fix manually. The upgrade path today requires the user to orchestrate multiple commands and manual edits. These changes make upgrades self-service.

## Changes

### 1. Add `erk init --upgrade` flag

**Files:**
- `src/erk/cli/commands/init/__init__.py` (add flag)
- `src/erk/cli/commands/init/main.py` (upgrade logic in `run_init()`)

When `--upgrade` is passed on an already-erkified repo:
- **Skip** config.toml rewrite (user may have customized it)
- **Run** artifact sync with `force=True` (ensures skills/hooks update)
- **Run** capability install (re-installs required capabilities like hooks)
- **Run** gitignore sync (adds any missing required entries, with prompts unless `--no-interactive`)
- **Update** `required-erk-uv-tool-version` file

The key difference from `--force`: `--force` rewrites config.toml (destructive), `--upgrade` preserves it but updates everything else.

Implementation: In the `already_erkified and not force` branch (line 528), instead of just printing "already configured", check if `upgrade` is True and run the upgrade path.

### 2. Add gitignore sync to `erk artifact sync`

**Files:**
- `src/erk/artifacts/sync.py` (add `_sync_gitignore()` function)
- `src/erk/cli/commands/artifact/sync_cmd.py` (call gitignore sync with confirmation)

Add a `_sync_gitignore()` function that:
- Uses the same `required_entries` list from health_checks.py (extract to shared constant in `init_utils.py`)
- Returns list of missing entries (pure function)

In `sync_cmd`, after `sync_artifacts()`:
- Call `_sync_gitignore()` to find missing entries
- If any missing, prompt user with `click.confirm()` listing the entries
- If confirmed, add them using `add_gitignore_entry()` from init_utils

Extract `REQUIRED_GITIGNORE_ENTRIES` to `src/erk/core/init_utils.py` so both health_checks.py and sync use the same source of truth.

### 3. Better remediation messages

**Files:**
- `src/erk/core/health_checks.py`

Update these checks:

**`check_gitignore_entries()` (line 694)**:
- Change remediation from `"Run 'erk init' to add missing entries"` to `"Run 'erk artifact sync' or 'erk init --upgrade'"`

**`check_user_prompt_hook()` (line 1033)**:
- The "missing unified hook script" case has NO remediation - add one
- Change message to: `"UserPromptSubmit hook command outdated"`
- Add remediation: `"Run 'erk artifact sync' to update hook commands"`

**`check_exit_plan_hook()` (line 1070)**:
- Change message from `"ExitPlanMode hook not configured"` to `"ExitPlanMode hook command outdated"` (when hooks exist but don't match current format)
- Change remediation from `"Run 'erk init'"` to `"Run 'erk artifact sync' to update hook commands"`

### 4. Make hook health check opt-in via `--check-hooks`

**Files:**
- `src/erk/cli/commands/doctor.py` (add flag, conditionally include check)
- `src/erk/core/health_checks.py` (parameterize `run_all_checks`)

Add `--check-hooks` flag to doctor command. The `check_hook_health()` call (line 1525) only runs when flag is present.

Implementation:
- Add `check_hooks: bool` parameter to `run_all_checks()`
- Only append `check_hook_health(repo_root)` when `check_hooks=True`
- Remove `"hooks"` from `REPO_SUBGROUPS["Hooks"]` default display (or keep the subgroup but it'll be empty when not opted in)

### 5. Bug fix: `_sync_hooks` skips updating old hooks

**File:** `src/erk/artifacts/sync.py` (line 579-581)

The condition at line 580 is buggy:
```python
if not has_user_prompt_hook(settings) and not has_exit_plan_hook(settings):
    return []
```

`has_user_prompt_hook`/`has_exit_plan_hook` check for the **current** command version (exact match). When upgrading, old hooks fail this check → function returns early → hooks never updated. Line 574 already handles the "no hooks" case via marker detection. Remove lines 579-581.

## File Summary

| File | Change |
|------|--------|
| `src/erk/cli/commands/init/__init__.py` | Add `--upgrade` flag |
| `src/erk/cli/commands/init/main.py` | Upgrade logic branch |
| `src/erk/core/init_utils.py` | Extract `REQUIRED_GITIGNORE_ENTRIES` constant |
| `src/erk/artifacts/sync.py` | Fix `_sync_hooks` bug, add `_sync_gitignore()` |
| `src/erk/cli/commands/artifact/sync_cmd.py` | Gitignore sync with user confirmation |
| `src/erk/core/health_checks.py` | Better remediations, parameterize hook health check |
| `src/erk/cli/commands/doctor.py` | Add `--check-hooks` flag |

## Verification

1. `erk init --upgrade` on an already-erkified repo updates artifacts, hooks, gitignore without rewriting config.toml
2. `erk artifact sync` prompts to add missing gitignore entries
3. `erk doctor` shows improved remediation messages
4. `erk doctor` no longer shows hook health by default; `erk doctor --check-hooks` does
5. `erk artifact sync` successfully updates old-format hooks to new format (the bug fix)
6. Run existing tests: `pytest tests/unit/cli/commands/init/ tests/artifacts/test_sync.py tests/core/test_health_checks.py`

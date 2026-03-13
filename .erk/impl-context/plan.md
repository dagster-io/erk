# Fix `erk land --up` broken cd path for upstack navigation

## Context

When landing a PR with `--up` (`erk land -f -u`), the generated `land.sh` script has a hardcoded `cd` to the child branch's worktree. This breaks when:
1. The child branch has no separate worktree (stacked branches share one slot)
2. The branch name contains `/` (e.g., `plnd/fix-outdated-skill-content-03-12-1448`), causing the fallback `worktrees_dir / branch_name` to create a nested path like `/worktrees/plnd/fix-outdated...`

The execute phase (`_navigate_after_land`) exits immediately in execute mode without resolving/creating the worktree, so the shell script's `cd` fails.

**Root cause**: The architecture bakes the target path into the shell script at validation time, but for `--up` mode the path can't be reliably predicted — the worktree may need creation via slot allocation at execution time.

## Fix: Defer upstack navigation to execution time

### Change 1: `_navigate_after_land` — resolve worktree in execute mode
**File**: `src/erk/cli/commands/land_cmd.py` (lines 1226-1229)

Replace early exit with worktree resolution + stdout path output:
```python
# Before (broken):
if target_child_branch is not None:
    if skip_activation_output:
        raise SystemExit(0)  # <-- exits without resolving

# After (fixed):
if target_child_branch is not None:
    if skip_activation_output:
        # Resolve/create worktree, output path to stdout for shell script
        target_path = ctx.git.worktree.find_worktree_for_branch(...)
        if target_path is None:
            target_path, _ = ensure_branch_has_worktree(...)
        user_output(restack tip)  # stderr, visible to user
        machine_output(str(target_path), nl=False)  # stdout, captured by script
        raise SystemExit(0)
```

### Change 2: `render_land_execution_script` — command substitution for `--up`
**File**: `src/erk/cli/commands/land_cmd.py` (lines 1306-1404)

Add `upstack_navigation: bool` parameter. When True, capture stdout:
```shell
# Before (broken):
erk exec land-execute ... "$@" || return 1
cd /worktrees/plnd/fix-outdated-skill-content-03-12-1448

# After (fixed):
TARGET_DIR=$(erk exec land-execute ... "$@") || return 1
cd "$TARGET_DIR"
```

When False (trunk navigation, unchanged):
```shell
erk exec land-execute ... "$@" || return 1
cd /path/to/repo
```

This works because `user_output()` → stderr (visible), `machine_output()` → stdout (captured by `$()`).

### Change 3: `_land_target` — defer path for `--up` mode
**File**: `src/erk/cli/commands/land_cmd.py` (lines 1064-1074, 1085, 1092-1103)

- When `target.target_child_branch is not None`: set `target_path = None`, `upstack_navigation = True`
- Remove buggy fallback `worktrees_dir / branch_name`
- Update dry-run message: `"Would navigate upstack to child branch '{name}'"` instead of broken path
- Pass `upstack_navigation` to `render_land_execution_script`

### Change 4: Update `render_land_execution_script` signature
**File**: `src/erk/cli/commands/land_cmd.py`

`target_path: Path` → `target_path: Path | None`, add `upstack_navigation: bool`

## Tests

### Existing tests — add `upstack_navigation=False`
**File**: `tests/unit/cli/commands/land/test_render_land_script.py`

All 10 existing tests call `render_land_execution_script` without `upstack_navigation`. Add `upstack_navigation=False` to each call.

### Existing test — no changes needed
**File**: `tests/unit/cli/commands/land/test_cleanup_and_navigate.py`

`test_cleanup_and_navigate_skip_activation_output_with_up_flag` uses `is_current_branch=False`, which goes through the else branch at line 477 (never reaches `_navigate_after_land`). Unaffected by our changes.

### New tests to add

1. **`test_render_land_script.py`**: `test_render_land_execution_script_upstack_uses_command_substitution`
   - Pass `upstack_navigation=True`, `target_path=None`
   - Assert `TARGET_DIR=$(` in script and `cd "$TARGET_DIR"` in script
   - Assert no hardcoded `cd /` path

2. **`test_render_land_script.py`**: `test_render_land_execution_script_non_upstack_uses_hardcoded_cd`
   - Pass `upstack_navigation=False`, `target_path=Path("/repo")`
   - Assert `cd /repo` in script, no `TARGET_DIR`

3. **`test_cleanup_and_navigate.py`**: Test execute mode with `--up` and `is_current_branch=True`
   - Setup FakeGit with child worktree existing
   - Call `_cleanup_and_navigate` with `skip_activation_output=True`, `target_child_branch`, `is_current_branch=True`
   - Capture stdout, assert resolved worktree path is output

## Verification

1. Run land script tests: `pytest tests/unit/cli/commands/land/test_render_land_script.py`
2. Run cleanup/navigate tests: `pytest tests/unit/cli/commands/land/test_cleanup_and_navigate.py`
3. Run all land tests: `pytest tests/unit/cli/commands/land/`
4. Run ty type checker on land_cmd.py

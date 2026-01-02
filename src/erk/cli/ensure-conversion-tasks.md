# Ensure Class Conversion Tasks

**Purpose**: Track conversion of manual error checking to use the centralized Ensure class.
**Status**: IN_PROGRESS
**Last Updated**: 2025-11-26

## Status Legend

- [ ] Not started
- [WIP] Work in progress
- [x] Completed

---

## Phase 1: New Ensure Methods

### Priority 1: High-Value Methods (8+ uses)

#### Task 1.1: Implement Ensure.mutually_exclusive_flags()

- [ ] Write method implementation
- [ ] Add unit tests (success case, multiple flags set, custom message)
- [ ] Document in method docstring
- **Usage**: 8 occurrences (wt/create, stack/consolidate, stack/move, stack/split)
- **Signature**: `mutually_exclusive_flags(flags: dict[str, bool | Any], error_message: str | None = None) -> None`

#### Task 1.2: Implement Ensure.not_detached_head()

- [ ] Write method implementation with type narrowing
- [ ] Add unit tests (on branch, detached HEAD, custom operation name)
- [ ] Document in method docstring
- **Usage**: 4 occurrences (stack/consolidate, stack/move, wt/delete)
- **Signature**: `not_detached_head(ctx: ErkContext, branch: str | None, operation_name: str) -> str`
- **Returns**: Narrowed type `str` (from `str | None`)

#### Task 1.3: Implement Ensure.clean_working_tree()

- [ ] Write method implementation with allow_force parameter
- [ ] Add unit tests (clean tree, uncommitted changes, force override)
- [ ] Document in method docstring
- **Usage**: 6 occurrences (navigation_helpers, stack/move, stack/split)
- **Signature**: `clean_working_tree(ctx: ErkContext, path: Path, operation_name: str | None = None, allow_force: bool = False) -> None`

#### Task 1.4: Implement Ensure.graphite_enabled()

- [ ] Write method implementation
- [ ] Add unit tests (enabled, disabled)
- [ ] Document in method docstring
- **Usage**: 3 occurrences (navigation_helpers, wt/delete)
- **Signature**: `graphite_enabled(ctx: ErkContext) -> None`
- **Error**: "This command requires Graphite to be enabled. Run 'erk config set use_graphite true'"

### Priority 2: Medium-Value Methods (2-4 uses)

#### Task 1.5: Implement Ensure.branch_tracked_by_graphite()

- [ ] Write method implementation with type narrowing
- [ ] Add unit tests (tracked branch, untracked branch)
- [ ] Document in method docstring
- **Usage**: 2 occurrences (stack/consolidate)
- **Signature**: `branch_tracked_by_graphite(ctx: ErkContext, repo_root: Path, branch: str) -> list[str]`
- **Returns**: Stack branches (narrows from `list[str] | None`)

#### Task 1.6: Implement Ensure.in_repo()

- [ ] Write method implementation
- [ ] Add unit tests (in repo, NoRepoSentinel)
- [ ] Document in method docstring
- **Usage**: 4 occurrences (context.py, pr/checkout, config)
- **Signature**: `in_repo(ctx: ErkContext) -> None`

#### Task 1.7: Implement Ensure.global_config_exists()

- [ ] Write method implementation with type narrowing
- [ ] Add unit tests (config exists, config None)
- [ ] Document in method docstring
- **Usage**: 4 occurrences (init, config, core)
- **Signature**: `global_config_exists(ctx: ErkContext) -> GlobalConfig`

#### Task 1.8: Implement Ensure.not_trunk_branch()

- [ ] Write method implementation
- [ ] Add unit tests (trunk branch, non-trunk branch)
- [ ] Document in method docstring
- **Usage**: 1-2 occurrences (wt/create)
- **Signature**: `not_trunk_branch(ctx: ErkContext, repo_root: Path, branch: str) -> None`

---

## Phase 2: File Conversions

### High Priority (20+ patterns each)

#### Task 2.1: Convert wt/create_cmd.py (30+ patterns)

- [ ] Lines 556-561: Replace manual check with `Ensure.mutually_exclusive_flags()` for --from-\* flags
- [ ] Lines 564-566: Replace manual check with `Ensure.mutually_exclusive_flags()` for --json/--script
- [ ] Lines 574-582: Replace manual check with `Ensure.mutually_exclusive_flags()` for --copy-plan
- [ ] Lines 101-108: Replace manual check with `Ensure.not_trunk_branch()`
- [ ] Lines 276: Replace None check with `Ensure.not_detached_head()` (already uses Ensure.not_none at line 610)
- [ ] Lines 587-594: Replace .exists()/.is_dir() checks with `Ensure.path_is_dir()` for .impl directory
- [ ] Lines 610-612: Keep as-is (already uses `Ensure.not_none()` correctly)
- [ ] Run tests: `uv run pytest tests/commands/workspace/test_create.py`
- [ ] Verify no regressions

#### Task 2.2: Convert stack/consolidate_cmd.py (15+ patterns)

- [ ] Lines 153-159: Replace manual check with `Ensure.mutually_exclusive_flags({"--down": down, "BRANCH": branch is not None})`
- [ ] Lines 165-168: Replace None check with `Ensure.not_detached_head(ctx, current_branch, "consolidate")`
- [ ] Lines 176-181: Replace None check with `stack_branches = Ensure.branch_tracked_by_graphite(ctx, repo.root, current_branch)`
- [ ] Lines 184-193: Keep as-is (nice formatted stack display, use `Ensure.invariant()` wrapper)
- [ ] Lines 202-212: Keep as-is or use `Ensure.invariant(name not in existing_names, msg)`
- [ ] Lines 231-241: Consider refactoring to `Ensure.clean_working_tree()` for each worktree in loop
- [ ] Run tests: `uv run pytest tests/commands/stack/`
- [ ] Verify no regressions

#### Task 2.3: Convert implement.py (25+ patterns)

- [ ] Lines 373-375: Replace .exists() check with `Ensure.path_exists(ctx, plan_file, ...)`
- [ ] Lines 632: Use `Ensure.not_none()` for wt_path
- [ ] Lines 708: Use `Ensure.not_none()` for target_info.issue_number
- [ ] Lines 866: Use `Ensure.not_none()` for wt_path
- [ ] Audit all None checks for conversion opportunities
- [ ] Run tests: `uv run pytest tests/commands/test_implement.py` (if exists)
- [ ] Verify no regressions

### Medium Priority (10-20 patterns each)

#### Task 2.4: Convert navigation_helpers.py

- [ ] Lines 14-28: Delete `ensure_graphite_enabled()` function after converting callers
- [ ] Lines 31-42: Delete `check_clean_working_tree()` function after converting callers
- [ ] Lines 45-68: Delete `verify_pr_merged()` function OR convert to `Ensure.pr_merged()` if implementing
- [ ] Lines 212-214: Use `Ensure.not_none()` in navigate_upstack
- [ ] Lines 246-254: Use `Ensure.not_none()` in navigate_downstack (multiple checks)
- [ ] Update up.py and down.py to call Ensure methods directly
- [ ] Run tests: `uv run pytest tests/commands/navigation/`
- [ ] Verify no regressions

#### Task 2.5: Convert stack/move_cmd.py

- [ ] Lines 59-61: Replace with `Ensure.mutually_exclusive_flags()`
- [ ] Lines 115: Replace with `Ensure.not_detached_head()`
- [ ] Lines 119-124: Replace with `Ensure.clean_working_tree(ctx, source_wt, "move", allow_force=force)`
- [ ] Lines 138: Replace with `Ensure.clean_working_tree(ctx, target_wt, "move", allow_force=force)`
- [ ] Lines 186: Replace with `Ensure.clean_working_tree()`
- [ ] Run tests: `uv run pytest tests/commands/stack/test_move.py`
- [ ] Verify no regressions

#### Task 2.6: Convert stack/split_old/command.py

- [ ] Lines 32-37: Replace with `Ensure.mutually_exclusive_flags({"--up": up, "--down": down})`
- [ ] Lines 64-67: Replace with `Ensure.clean_working_tree(ctx, current_worktree, "split")`
- [ ] Run tests: `uv run pytest tests/commands/stack/test_split.py`
- [ ] Verify no regressions

### Lower Priority (5-10 patterns each)

#### Task 2.7: Convert wt/delete_cmd.py

- [ ] Lines 132-137: Replace with `Ensure.graphite_enabled(ctx)`
- [ ] Lines 143-147: Replace with `Ensure.not_detached_head()`
- [ ] Run tests: `uv run pytest tests/commands/workspace/test_delete.py`
- [ ] Verify no regressions

#### Task 2.8: Convert commands/config.py

- [ ] Lines 104-107: Replace with `Ensure.global_config_exists(ctx)`
- [ ] Lines 157-160: Replace with `Ensure.global_config_exists(ctx)`
- [ ] Run tests: `uv run pytest tests/commands/test_config.py`
- [ ] Verify no regressions

#### Task 2.9: Convert commands/init.py

- [ ] Lines 171-175: Replace with `Ensure.global_config_exists(ctx)`
- [ ] Lines 228-232: Replace with `Ensure.global_config_exists(ctx)`
- [ ] Lines 248-252: Replace with `Ensure.global_config_exists(ctx)`
- [ ] Lines 266-268: Replace with `Ensure.path_not_exists()` (adjust condition logic)
- [ ] Run tests: `uv run pytest tests/commands/test_init.py`
- [ ] Verify no regressions

#### Task 2.10: Convert commands/wt/current_cmd.py

- [ ] Lines 28-29: Add error message and replace with `Ensure.not_none(wt_info, "Not in a worktree")`
- [ ] Run tests: `uv run pytest tests/commands/workspace/test_current.py`
- [ ] Verify no regressions

#### Task 2.11: Convert commands/pr/checkout_cmd.py

- [ ] Line 43: Replace NoRepoSentinel check with `Ensure.in_repo(ctx)`
- [ ] Run tests: `uv run pytest tests/commands/pr/`
- [ ] Verify no regressions

#### Task 2.12: Convert cli/core.py

- [ ] Lines 18-19: Replace with `Ensure.global_config_exists(ctx)`
- [ ] Run tests: `uv run pytest tests/unit/cli/`
- [ ] Verify no regressions

---

## Phase 3: Final Cleanup

#### Task 3.1: Audit for remaining patterns

- [ ] Search for `raise SystemExit(1)` across CLI files
- [ ] Search for manual None checks followed by user_output
- [ ] Search for manual path existence checks
- [ ] Create follow-up tasks for any missed patterns

#### Task 3.2: Consistency pass

- [ ] Verify all error messages use red "Error: " prefix
- [ ] Verify all Ensure method docstrings are complete
- [ ] Verify all type narrowing methods work with ty
- [ ] Update any developer documentation

#### Task 3.3: Final validation

- [ ] Run full test suite: `uv run pytest`
- [ ] Run type checker: `uv run ty`
- [ ] Verify no regressions in any tests
- [ ] Mark project as COMPLETED

---

## Implementation Notes

### Test Pattern to Follow

From `tests/unit/cli/test_ensure.py`:

```python
def test_exits_when_condition_false(self) -> None:
    """Ensure.method raises SystemExit when condition fails."""
    with pytest.raises(SystemExit) as exc_info:
        Ensure.method(...)
    assert exc_info.value.code == 1

def test_error_message_output(self, capsys: pytest.CaptureFixture[str]) -> None:
    """Ensure.method outputs error message to stderr."""
    with pytest.raises(SystemExit):
        Ensure.method(...)

    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "expected message" in captured.err
```

### Type Narrowing Example

Methods that return values should narrow types:

```python
# Before: branch: str | None = ctx.git.get_current_branch(ctx.cwd)
# After:  branch: str = Ensure.not_detached_head(ctx, ctx.git.get_current_branch(ctx.cwd), "operation")
```

### Mutually Exclusive Flags Example

```python
# Before:
if flag_count > 1:
    user_output("Error: Only one of --current, --branch, or --worktree can be specified")
    raise SystemExit(1)

# After:
Ensure.mutually_exclusive_flags({
    "--current": current,
    "--branch": branch is not None,
    "--worktree": worktree is not None
})
```

---

## Progress Tracking

| Phase                     | Tasks  | Completed | Remaining |
| ------------------------- | ------ | --------- | --------- |
| Phase 1: New Methods      | 8      | 0         | 8         |
| Phase 2: File Conversions | 12     | 0         | 12        |
| Phase 3: Final Cleanup    | 3      | 0         | 3         |
| **TOTAL**                 | **23** | **0**     | **23**    |

**Last Updated**: 2025-11-26
**Current Focus**: Phase 1 - New Ensure Methods
**Next Up**: Task 1.1 - Implement Ensure.mutually_exclusive_flags()

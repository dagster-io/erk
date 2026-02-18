# Migrate `tests/unit/cli/test_navigation_helpers.py` (16 Mock instances)

**Objective**: #7129 - Eliminate Excessive Mocking from Unit Tests
**Step**: 4.2 - Migrate `tests/unit/cli/test_navigation_helpers.py` (16 Mock instances)
**Depends on**: Step 4.1 (PR #7378) evaluates FakeClickContext vs real `click.Context`. That PR uses real `click.Context` objects. This plan follows the same pattern.

## Context

`tests/unit/cli/test_navigation_helpers.py` contains **16 `Mock` instances** across 8 test functions, all in the shell completion tests (`complete_branch_names` and `complete_plan_files`). Each test creates a `Mock(spec=click.Context)` and a bare `Mock()` for the root context:

```python
mock_ctx = Mock(spec=click.Context)
mock_root_ctx = Mock()
mock_root_ctx.obj = ctx_obj
mock_ctx.find_root.return_value = mock_root_ctx
```

The remaining tests in this file (delete_branch_and_worktree, activate_root_repo, render_deferred_deletion_commands, get_slot_name_for_worktree, validate_for_deletion, unallocate_worktree_and_branch) already use proper fakes (FakeGit, context_for_test, FakeScriptWriter, FakeGitHub) and need no changes.

## Why Real Click Context Instead of a Fake

Click's `Context` is a simple value object with well-defined parent-child relationships. Using real `click.Context` objects:
- Exercises the actual `find_root()` traversal that production code relies on
- Requires no custom fake class (Click handles the parent-child chain natively)
- Is the pattern established by step 4.1 (PR #7378)

## Changes

### File: `tests/unit/cli/test_navigation_helpers.py`

#### 1. Remove Mock import (line 5)

**Remove:**
```python
from unittest.mock import Mock
```

No other code in this file uses `Mock` after the migration.

#### 2. Replace all 8 Mock context blocks with real Click contexts

Each of the 8 completion test functions has the identical pattern. Replace every occurrence of:

```python
    # Create mock Click context
    mock_ctx = Mock(spec=click.Context)
    mock_root_ctx = Mock()
    mock_root_ctx.obj = ctx_obj
    mock_ctx.find_root.return_value = mock_root_ctx
```

with:

```python
    # Create real Click context with parent chain for find_root()
    root_ctx = click.Context(click.Command("root"))
    root_ctx.obj = ctx_obj
    child_ctx = click.Context(click.Command("complete"), parent=root_ctx)
```

And update the function call from `mock_ctx` to `child_ctx`:

```python
# Before:
result = complete_branch_names(mock_ctx, None, "")
# After:
result = complete_branch_names(child_ctx, None, "")
```

#### 3. Affected test functions (all 8)

| # | Test Function | Lines (approx) |
|---|---|---|
| 1 | `test_complete_branch_names_local_branches` | 79-86 |
| 2 | `test_complete_branch_names_remote_branches_strip_prefix` | 116-123 |
| 3 | `test_complete_branch_names_deduplication` | 153-160 |
| 4 | `test_complete_branch_names_filters_by_prefix` | 191-198 |
| 5 | `test_complete_plan_files_finds_markdown_files` | 233-240 |
| 6 | `test_complete_plan_files_no_markdown_files` | 274-281 |
| 7 | `test_complete_plan_files_filters_by_prefix` | 316-323 |
| 8 | `test_complete_plan_files_returns_sorted_results` | 358-365 |

The transformation is identical for all 8 functions.

## How `shell_completion_context` Works (Why Real Context Is Correct)

The completion functions (`complete_branch_names`, `complete_plan_files`) call `shell_completion_context(ctx)` from `src/erk/cli/commands/completions.py`, which:

1. Calls `ctx.find_root()` to get the root Click context
2. Reads `root_ctx.obj` to get the `ErkContext`
3. If `obj` is None (resilient parsing mode), creates a fresh `ErkContext`

With real Click contexts:
- `child_ctx.find_root()` traverses the parent chain and returns `root_ctx`
- `root_ctx.obj` returns the `ctx_obj` we assigned
- This exercises the real Click parent-child traversal, unlike the Mock which just returns a canned value

## Files NOT Changing

- `src/erk/cli/commands/completions.py` - No production code changes needed
- `src/erk/cli/commands/navigation_helpers.py` - No production code changes needed
- All non-completion tests in this file - Already use proper fakes
- Any files in `tests/fakes/` - No new fake class needed

## Verification

1. Run the specific test file:
   ```
   pytest tests/unit/cli/test_navigation_helpers.py -v
   ```

2. Confirm no `Mock` or `unittest.mock` imports remain:
   ```
   grep -n "mock\|Mock" tests/unit/cli/test_navigation_helpers.py
   ```
   Should return zero results.

3. Run the broader CLI test suite:
   ```
   pytest tests/unit/cli/ -v
   ```

4. Run type checker:
   ```
   ty check tests/unit/cli/test_navigation_helpers.py
   ```
# Fix: Allow `--delete-current` for closed PRs

## Problem

`erk down --delete-current` fails with "PR is not merged" error when the PR is **closed** (not merged). Closed PRs should be deletable since the work was intentionally abandoned.

**Current behavior:**
```
$ erk down --delete-current
Error: Pull request for branch 'minimal-change-fix-for-gtpr-sub-25-11-26' is not merged.
Only merged branches can be deleted with --delete-current.
```

**Root cause:** `navigation_helpers.py:62` checks `if pr_info.state != "MERGED"` which blocks "CLOSED" state.

## Implementation

### 1. Update `verify_pr_merged()` in `navigation_helpers.py`

**File:** `src/erk/cli/commands/navigation_helpers.py`

Change lines 62-69 from:
```python
if pr_info.state != "MERGED":
    # Keep error for unmerged PRs (safety mechanism remains)
    user_output(
        click.style("Error: ", fg="red")
        + f"Pull request for branch '{branch}' is not merged.\n"
        "Only merged branches can be deleted with --delete-current."
    )
    raise SystemExit(1)
```

To:
```python
if pr_info.state not in ("MERGED", "CLOSED"):
    # Block deletion only for open PRs (safety mechanism)
    user_output(
        click.style("Error: ", fg="red")
        + f"Pull request for branch '{branch}' is still open.\n"
        "Only merged or closed branches can be deleted with --delete-current."
    )
    raise SystemExit(1)
```

### 2. Rename function for clarity

Rename `verify_pr_merged` → `verify_pr_completed` to reflect it now accepts both merged and closed PRs.

Update call sites:
- `src/erk/cli/commands/down.py:12,66` (import + call)
- `src/erk/cli/commands/up.py:11,85` (import + call)

### 3. Add test for CLOSED state

**File:** `tests/commands/navigation/test_down.py`

Add new test `test_down_delete_current_pr_closed()` based on `test_down_delete_current_success()` but with `state="CLOSED"`:

```python
def test_down_delete_current_pr_closed() -> None:
    """Test --delete-current succeeds when PR is closed (not merged)."""
    # ... same setup as test_down_delete_current_success
    # But with state="CLOSED" instead of "MERGED"
```

## Files to Modify

1. `src/erk/cli/commands/navigation_helpers.py` - Fix condition + rename function
2. `src/erk/cli/commands/down.py` - Update import + call
3. `src/erk/cli/commands/up.py` - Update import + call
4. `tests/commands/navigation/test_down.py` - Add test for CLOSED state

## Verification

Run scoped tests:
```bash
uv run pytest tests/commands/navigation/test_down.py -v
```
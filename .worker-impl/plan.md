# Plan: Unify `local-wt` Column to `wt` with Color-Coded Display

## Overview

Modify the `erk dash` command to show worktree/branch names for **both local and remote** runs in a unified `wt` column, using color to distinguish between them:

- **Yellow**: Local worktree exists on this machine
- **Grey/Dim**: Remote-only (branch exists on GitHub but no local worktree)

## Current State

- **Column name**: `local-wt`
- **Data source**:
  1. Local worktrees (scanned via `.impl/issue.json`)
  2. `worktree_name` field in plan-header metadata (issue body)
- **Display logic**: Only shows name if worktree exists locally; otherwise shows `-`
- **Problem**: When plans are submitted via `erk submit`, the branch name is NOT stored in plan-header, so remote-only runs show `-`

## Implementation Steps

### Step 1: Modify `erk submit` to Store Branch Name in Plan-Header

**File**: `src/erk/cli/commands/submit.py`

Update the submission flow to store the `branch_name` in the plan-header metadata after creating the branch:

1. After successfully creating/using a branch, call `update_plan_header_worktree_name()` to store the branch name
2. This ensures every submitted plan has a worktree-like name stored in the issue body

**Key location**: After line ~395 (branch pushed to remote) or ~366 (existing branch case)

### Step 2: Add `update_plan_header_worktree_name()` Function

**File**: `packages/erk-shared/src/erk_shared/github/metadata.py`

Create a helper function to update just the `worktree_name` field in an existing plan-header:

```python
def update_plan_header_worktree_name(
    existing_body: str,
    worktree_name: str,
) -> str:
    """Update the worktree_name field in an existing plan-header block."""
```

This function should:
1. Parse the existing plan-header from the issue body
2. Update only the `worktree_name` field
3. Return the updated issue body

### Step 3: Update Display Logic in `erk dash`

**File**: `src/erk/cli/commands/plan/list_cmd.py`

**3a. Rename column**: Change `local-wt` to `wt`

**3b. Update `format_worktree_name_cell()`** (lines 109-123):

```python
def format_worktree_name_cell(worktree_name: str, exists_locally: bool) -> str:
    """Format worktree name with existence styling.

    Returns:
        - Exists locally: "[yellow]name[/yellow]"
        - Remote only: "[dim]name[/dim]"
        - No worktree: "-"
    """
    if not worktree_name:
        return "-"
    if exists_locally:
        return f"[yellow]{worktree_name}[/yellow]"
    return f"[dim]{worktree_name}[/dim]"
```

**3c. Update call site** (line 350): Pass `worktree_name` even when not local

Current:
```python
worktree_name_cell = format_worktree_name_cell(worktree_name, exists_locally)
```

The logic already extracts `worktree_name` from plan-header when not local (lines 339-344), so this should work without changes once `format_worktree_name_cell` is updated.

### Step 4: Update GitHub API to Save Worktree Name

**File**: `src/erk/integrations/github/service.py` (or wherever the GitHub ABC is implemented)

Add a method to update plan issue body:
```python
def update_plan_worktree_name(
    repo_root: Path,
    issue_number: int,
    worktree_name: str,
) -> None:
```

### Step 5: Update Tests

**Files**:
- `tests/commands/test_dash.py` - Update column name expectations, add test for remote-only display
- `tests/commands/test_submit.py` - Add test that submit stores worktree_name
- `packages/erk-shared/tests/github/test_metadata.py` - Test new update function

## Files to Modify

1. `src/erk/cli/commands/submit.py` - Store branch name in plan-header
2. `packages/erk-shared/src/erk_shared/github/metadata.py` - Add update function
3. `src/erk/cli/commands/plan/list_cmd.py` - Update column name and display logic
4. `src/erk/integrations/github/abc.py` - Add ABC method (if needed)
5. `src/erk/integrations/github/service.py` - Implement update method
6. `tests/commands/test_dash.py` - Update tests
7. `tests/commands/test_submit.py` - Add tests

## Visual Result

Before:
```
┃ local-wt                                      ┃
├───────────────────────────────────────────────┤
│ 1758-optimize-github-graphql-qu-11-30-1820    │  (yellow - local)
│ -                                             │  (remote-only, no info)
│ -                                             │  (never implemented)
```

After:
```
┃ wt                                            ┃
├───────────────────────────────────────────────┤
│ 1758-optimize-github-graphql-qu-11-30-1820    │  (yellow - local)
│ 1815-fix-worker-impl-appearing-11-30-1820    │  (grey/dim - remote-only)
│ -                                             │  (never implemented)
```
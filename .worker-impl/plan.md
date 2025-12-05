# Plan: Fix `--worktree-name` to Set Both Worktree and Branch Name

## Problem

When running `erk implement <issue> --worktree-name <name>`:
- Current behavior: Uses `<name>` for worktree directory but still uses the GitHub-linked branch
- Desired behavior: Uses `<name>` for BOTH worktree directory AND branch (creates new branch)

This causes the error "Branch '...' is already checked out at..." when trying to create a second worktree for the same issue.

## Solution

Rename `--worktree-name` to `--wt-name` and fix the logic to set both worktree directory and branch name when provided.

## Implementation

### 1. Rename parameter in `implement.py`

**File:** `/Users/schrockn/code/erk/src/erk/cli/commands/implement.py`

**Lines 854-859** - Change parameter definition:
```python
@click.option(
    "--wt-name",
    type=str,
    default=None,
    help="Override name for both worktree directory and branch (creates new branch, ignores linked branch)",
)
```

**Lines 901-911** - Update function signature:
```python
def implement(
    ctx: ErkContext,
    target: str,
    wt_name: str | None,  # renamed from worktree_name
    ...
```

### 2. Fix core naming logic

**Lines 516-531** - Reorder logic to check user-provided name FIRST:

```python
if wt_name:
    # User explicitly provided name - use for BOTH worktree and branch
    # This creates a new branch, ignoring any existing linked branch
    name = sanitize_worktree_name(wt_name)
    branch = name
    # Clear linked_branch_name so downstream logic creates new branch
    linked_branch_name = None
elif linked_branch_name:
    # No user override - use the GitHub-linked branch
    branch = linked_branch_name
    name = sanitize_worktree_name(linked_branch_name)
else:
    # Auto-generate name from plan source
    name = ensure_unique_worktree_name_with_date(
        plan_source.base_name, repo.worktrees_dir, ctx.git
    )
    branch = name
```

Key change: `linked_branch_name = None` ensures `use_existing_branch` becomes `False` (line 537), triggering new branch creation.

### 3. Update call sites

Update all calls to `_create_worktree_with_plan_content()`:
- Line 724-734 (issue mode)
- Line 808-817 (file mode)

Change parameter from `worktree_name=` to `wt_name=`.

### 4. Update error messages

**Lines 544-555** - Update references from `--worktree-name` to `--wt-name`.

### 5. Update tests

**File:** `/Users/schrockn/code/erk/tests/commands/test_implement.py`

1. Update existing test `test_implement_from_issue_with_custom_name` to use `--wt-name`
2. Add test: `test_implement_issue_with_linked_branch_wt_name_creates_new_branch`
   - Setup: Issue with existing linked branch
   - Action: Call with `--wt-name my-new-attempt`
   - Assert: New branch `my-new-attempt` created (not the linked branch)

## Critical Files

- `/Users/schrockn/code/erk/src/erk/cli/commands/implement.py` - Main changes
- `/Users/schrockn/code/erk/tests/commands/test_implement.py` - Test updates
- `/Users/schrockn/code/erk/tests/fakes/issue_link_branches.py` - Reference for existing branch testing

## Skills to Load

- `dignified-python-313` - Python code style
- `fake-driven-testing` - Test patterns
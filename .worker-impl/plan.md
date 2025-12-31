# Plan: Delete `post-plan-comment` (Objective #3552, Step 1.1)

Part of [Objective #3552](https://github.com/dagster-io/erk/issues/3552): Delete 13 Dead erk exec Commands

## Verification (PASSED)

Command is confirmed dead:
- Only 2 files reference `post-plan-comment` or `post_plan_comment`:
  - `src/erk/cli/commands/exec/scripts/post_plan_comment.py` (the script itself)
  - `src/erk/cli/commands/exec/group.py` (registration - we're removing this)
- No test files exist
- No .md documentation references
- No workflow references
- No programmatic invocations

## Orphaned Utility Found

`create_plan_issue_block` in `erk_shared.github.metadata` is only used by:
1. `post_plan_comment.py` (dead)
2. `test_metadata_blocks.py` (test for it)

This function and its test can be deleted as orphaned code.

## Execution Steps

### Step 1: Remove from group.py

**File:** `src/erk/cli/commands/exec/group.py`

Remove import (line 73):
```python
from erk.cli.commands.exec.scripts.post_plan_comment import post_plan_comment
```

Remove registration (line 150):
```python
exec_group.add_command(post_plan_comment, name="post-plan-comment")
```

### Step 2: Delete Script

```bash
rm src/erk/cli/commands/exec/scripts/post_plan_comment.py
```

### Step 3: Delete Orphaned Utility

**File:** `packages/erk-shared/src/erk_shared/github/metadata.py`

Remove the `create_plan_issue_block` function.

**File:** `packages/erk-shared/src/erk_shared/github/metadata_blocks.py`

Check if this is the source - remove `create_plan_issue_block` from there too.

**File:** `tests/unit/gateways/github/test_metadata_blocks.py`

Remove tests for `create_plan_issue_block`.

### Step 4: Verify

```bash
uv run pyright src/erk/cli/commands/exec/
uv run pytest tests/unit/cli/commands/exec/ -x
uv run pytest tests/unit/gateways/github/test_metadata_blocks.py -x
```

## Files to Modify

1. `src/erk/cli/commands/exec/group.py` - Remove import and registration
2. `src/erk/cli/commands/exec/scripts/post_plan_comment.py` - DELETE
3. `packages/erk-shared/src/erk_shared/github/metadata.py` - Remove `create_plan_issue_block`
4. `packages/erk-shared/src/erk_shared/github/metadata_blocks.py` - Remove `create_plan_issue_block` if present
5. `tests/unit/gateways/github/test_metadata_blocks.py` - Remove orphaned tests
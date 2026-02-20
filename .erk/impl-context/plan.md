# Fix .erk/impl-context/ not being cleaned from git during local implementation

## Context

After `erk implement -d` runs locally, `.erk/impl-context/` remains committed on the branch. Two cleanup layers conflict:

1. `setup_impl_from_issue.py` line 204: `shutil.rmtree(impl_context_dir)` removes the directory from the **filesystem only** (not from git)
2. `/erk:plan-implement` Step 2d: checks `[ -d .erk/impl-context/ ]` — but since `shutil.rmtree` already deleted the local copy, the check returns false, `git rm` never runs, and the files stay committed

The fix is to remove the premature `shutil.rmtree` so Step 2d can find the directory still present and properly run `git rm -rf` + commit + push.

## Change

**File**: `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`

Remove lines 203-204:
```python
# Clean up - this directory shouldn't persist into implementation
shutil.rmtree(impl_context_dir)
```

Replace with a comment:
```python
# Do not delete here — Step 2d in plan-implement.md handles git rm + commit + push
```

Also remove `import shutil` on line 22 (it becomes unused after this change).

**No changes** to `.claude/commands/erk/plan-implement.md` — Step 2d's `[ -d .erk/impl-context/ ]` check is already correct.

## Verification

- Run existing `setup_impl` and `plan_save` tests
- Run `ruff` and `ty` on the changed file
- Manual: run `erk implement -d` on a draft-PR plan and confirm `git rm` fires in Step 2d

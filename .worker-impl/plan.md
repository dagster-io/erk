# Complete Git API Consolidation: Trunk Branch Detection

## Summary

Finish the in-progress consolidation of duplicate Git APIs for trunk branch detection. We've already renamed `detect_default_branch` and `get_trunk_branch` to `detect_trunk_branch` and `validate_trunk_branch` across production code. The remaining work is updating integration tests and running verification.

## Background

The Git interface in `packages/erk-shared/src/erk_shared/git/abc.py` had two methods doing essentially the same thing:

| Old Method | New Method | Purpose |
|------------|------------|---------|
| `detect_default_branch(repo_root, configured=None)` | Split into two below | Did both detection and validation |
| `get_trunk_branch(repo_root)` | `detect_trunk_branch(repo_root)` | Auto-detect only, never fails |
| (validation part) | `validate_trunk_branch(repo_root, name)` | Validate configured branch exists |

## Completed Work

1. **abc.py** - Interface updated with new method signatures
2. **real.py** - Implementation updated
3. **FakeGit implementations** (3 files) - Updated:
   - `src/erk/core/git/fake.py`
   - `tests/fakes/git.py`
   - `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py`
4. **Wrapper classes** - Updated:
   - `src/erk/core/git/printing.py`
   - `src/erk/core/git/dry_run.py`
5. **Production call sites** - All updated
6. **Unit tests** - Partially updated:
   - `tests/core/detection/test_detect_default_branch.py` - Done
   - `tests/unit/fakes/test_fake_git.py` - Done

## Remaining Work

### Step 1: Update Integration Tests

**File:** `tests/integration/test_real_git.py`

The file has ~10 tests for the old methods that need consolidation:

**Tests to rename/update (detect_default_branch → detect_trunk_branch):**
- `test_detect_default_branch_main` → `test_detect_trunk_branch_main`
- `test_detect_default_branch_master` → `test_detect_trunk_branch_master`
- `test_detect_default_branch_with_remote_head` → `test_detect_trunk_branch_with_remote_head`
- `test_detect_default_branch_neither_exists` → **Update behavior**: Old method raised `RuntimeError`, new method returns `"main"` as fallback

**Tests to rename (get_trunk_branch → detect_trunk_branch):**
These are now duplicates of the above since both old methods consolidated into one:
- `test_get_trunk_branch_with_symbolic_ref_main` - Duplicate, can be removed
- `test_get_trunk_branch_with_symbolic_ref_master` - Duplicate, can be removed
- `test_get_trunk_branch_with_symbolic_ref_custom` → Keep as `test_detect_trunk_branch_with_symbolic_ref_custom`
- `test_get_trunk_branch_fallback_to_main` - Duplicate, can be removed
- `test_get_trunk_branch_fallback_to_master` → Keep as `test_detect_trunk_branch_fallback_to_master`
- `test_get_trunk_branch_both_branches_prefers_main` → Keep as `test_detect_trunk_branch_both_branches_prefers_main`
- `test_get_trunk_branch_final_fallback` → Keep, update assertion (returns "main", doesn't fail)

### Step 2: Run Tests

Run the test suite to verify all changes work correctly:
```bash
uv run pytest tests/core/detection/ tests/unit/fakes/test_fake_git.py tests/integration/test_real_git.py -v
```

### Step 3: Run Type Checker

Verify no type errors were introduced:
```bash
uv run pyright
```

## Key Behavior Change

The new `detect_trunk_branch` has a different failure mode than the old `detect_default_branch`:

| Scenario | Old Behavior | New Behavior |
|----------|--------------|--------------|
| Neither main nor master exists | Raises `RuntimeError` | Returns `"main"` (silent fallback) |

This is intentional - auto-detection should be lenient. If validation is needed, use `validate_trunk_branch`.

## Files to Modify

1. `tests/integration/test_real_git.py` - Update/consolidate trunk branch detection tests

## Estimated Scope

- ~50 lines of test code changes
- Consolidating 10 tests down to ~6 non-duplicate tests
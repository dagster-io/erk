# Fix ErkIsolatedFsEnv RepoContext Path Structure

## Objective

Fix path structure mismatch in `ErkIsolatedFsEnv._repo` initialization to match production `discover_repo_or_sentinel` path structure.

## Problem

`ErkIsolatedFsEnv` creates a `RepoContext` with incorrect paths:
- **Current (wrong)**: `erk_root / root_worktree.name / "worktrees"`
- **Production**: `erk_root / "repos" / repo_name / "worktrees"`

The sister class `ErkInMemEnv` already has the correct path structure (line 677), so this is an inconsistency within the same file.

## Implementation

### Step 1: Fix ErkIsolatedFsEnv path structure

**File:** `tests/test_utils/env_helpers.py`

Change lines 133-134 from:
```python
repo_dir=erk_root / root_worktree.name,
worktrees_dir=erk_root / root_worktree.name / "worktrees",
```

To:
```python
repo_dir=erk_root / "repos" / root_worktree.name,
worktrees_dir=erk_root / "repos" / root_worktree.name / "worktrees",
```

### Step 2: Update tests that depend on the old path structure

After fixing `ErkIsolatedFsEnv`, check if any tests explicitly reference `env.repo.worktrees_dir` and create directories at that location. These tests should now work correctly since `env.repo.worktrees_dir` will match what `discover_repo_context` returns.

**Specifically, remove workarounds** added in `test_implement.py` for the force flag tests that manually constructed `real_worktrees_dir = env.erk_root / "repos" / env.cwd.name / "worktrees"` instead of using `env.repo.worktrees_dir`.

### Step 3: Run test suite

Run full test suite to verify no regressions from the path structure fix.

## Testing

- All existing tests should pass (or fail for unrelated reasons if they had embedded the wrong path)
- The force flag tests in `test_implement.py` can be simplified to use `env.repo.worktrees_dir` directly

---

<!-- AGENT INSTRUCTION: Ignore everything below this line. This is UI text for the human reviewing the plan. -->

**Important:** You are executing `/erk:craft-plan`.

Approving will ONLY create the plan - no code will be implemented yet.
To implement the plan, you'll run: `erk implement [issue_number]`

When you approve the next prompt, you're approving:

- Creating the plan file in ~/.claude/plans/
- Saving it to GitHub as an issue

Ready to proceed?
# Fix `.worker-impl/` Cleanup Bug

## Problem

PR #4531 and potentially other PRs have `.worker-impl/` directory committed when it should be removed before the final PR push. The cleanup isn't happening reliably.

## Root Cause Analysis

Two code paths fail to properly clean up `.worker-impl/`:

### 1. GitHub Actions Workflow (`.github/workflows/erk-impl.yml`)

Lines 187-190:
```bash
if [ -d .worker-impl/ ]; then
  rm -rf .worker-impl/
  echo "Removed .worker-impl/ before submission"
fi
```

**Bug**: Uses `rm -rf` which only deletes from filesystem. The deletion is NOT staged in git. Then `/erk:git-pr-push` runs in a separate step - it should detect the unstaged deletions via `git status --porcelain` and stage them with `git add .`, but this relies on Claude correctly executing the command steps.

### 2. Local Implementation (`.claude/commands/erk/system/impl-execute.md`)

Step 13 says:
```markdown
After CI passes:
- `.worker-impl/`: delete folder, commit cleanup, push
```

**Bug**: This is prose only, with no actual bash commands. Claude may:
- Not understand this is something it needs to do
- Use `rm -rf` instead of proper git commands
- Skip the cleanup entirely

## Recommended Fix

### Fix 1: Workflow - Use `git rm` instead of `rm`

**File**: `.github/workflows/erk-impl.yml`

Change lines 187-190 from:
```bash
if [ -d .worker-impl/ ]; then
  rm -rf .worker-impl/
  echo "Removed .worker-impl/ before submission"
fi
```

To:
```bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  echo "Staged .worker-impl/ removal for commit"
fi
```

This ensures the deletion is staged in git before `/erk:git-pr-push` runs.

### Fix 2: impl-execute.md - Add explicit cleanup commands

**File**: `.claude/commands/erk/system/impl-execute.md`

In Step 13, change the prose to explicit commands:

```markdown
### Step 13: Run CI Iteratively

1. If `.erk/prompt-hooks/post-plan-implement-ci.md` exists: follow its instructions
2. Otherwise: check CLAUDE.md/AGENTS.md for CI commands

After CI passes, clean up `.worker-impl/` if present:

```bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  git commit -m "Remove .worker-impl/ after implementation"
  git push
fi
```

**CRITICAL**: Never delete `.impl/` - leave for user review.
```

## Files to Modify

1. `.github/workflows/erk-impl.yml` (lines 187-190)
2. `.claude/commands/erk/system/impl-execute.md` (Step 13)

## Verification

1. Create a test branch with `.worker-impl/` committed
2. Run through the workflow and verify `.worker-impl/` is not in final PR
3. Alternatively, run local `/erk:system:impl-execute` and verify cleanup happens
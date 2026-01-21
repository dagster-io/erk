# Plan: Update RELEASING.md for erk prepare workflow

> **Replans:** #5338

## Summary

Update RELEASING.md to support both manual branch creation (`release-X.Y.Z`) and `erk prepare` workflow (which creates `P{issue}-{slug}-{date}` branches).

## What Changed Since Original Plan

- PR #5339 was closed without merging - the implementation was not completed
- RELEASING.md remains in its original state with hardcoded branch names

## Investigation Findings

### Corrections to Original Plan

1. **Step 10 current command differs from assumption**: The actual command uses `erk br co master` not `git checkout master`:
   ```bash
   erk br co master && git merge release-X.Y.Z && git push origin master --tags
   ```

### Additional Details Discovered

1. Step 7 uses `erk pr submit` which already works with any branch name
2. The squash step (Step 5) uses `git reset --soft master` which works regardless of branch name
3. There's a tooling reference table at the end that could mention `erk prepare`

## Implementation Steps

### 1. Update Step 1 (lines 13-19) - Add both branch creation options

Replace the current Step 1 with:

```markdown
### 1. Create a Release Branch

**Option A - Manual:**
```bash
git checkout -b release-X.Y.Z
```

**Option B - Via plan workflow:**
```bash
erk prepare -d <plan-issue>
```
This creates a branch named `P{issue}-{slug}-{date}`.

Release work happens on a dedicated branch, not directly on master.
```

### 2. Update Step 10 (lines 105-113) - Use dynamic branch name

Replace the current Step 10 with:

```markdown
### 10. Merge to Master

After confirming the publish succeeded, merge from the release branch:

```bash
# Capture current branch name, then merge to master
RELEASE_BRANCH=$(git branch --show-current)
erk br co master && git merge "$RELEASE_BRANCH" && git push origin master --tags
```

> **Note:** If using `erk prepare`, the branch name will be `P{issue}-{slug}-{date}` instead of `release-X.Y.Z`.

Only merge to master after verifying the release works correctly.
```

## Critical File

- `RELEASING.md` - documentation update only (145 lines)

## Verification

1. Review the updated documentation for clarity and accuracy
2. Verify markdown renders correctly
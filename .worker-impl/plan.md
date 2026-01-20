# Plan: Update RELEASING.md for erk prepare workflow

## Problem

Step 10 hardcodes `release-X.Y.Z` branch name, but with `erk prepare` workflow, branches are named `P{issue}-{slug}-{date}` (e.g., `P5331-release-plan-erk-0-6-0-er-01-20-0756`).

## Changes

### 1. Update Step 1 - Add both branch creation options

Add note that `erk prepare` creates differently-named branches:

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

### 2. Update Step 10 - Use dynamic branch name

Replace hardcoded branch name with dynamic approach:

```markdown
### 10. Merge to Master

After confirming the publish succeeded, merge from the release branch:

```bash
# From the release branch, capture name then merge
RELEASE_BRANCH=$(git branch --show-current)
git checkout master
git merge "$RELEASE_BRANCH"
git push origin master --tags
```

> **Note:** If using `erk prepare`, the branch name will be `P{issue}-{slug}-{date}` instead of `release-X.Y.Z`.
```

## Critical File

- `RELEASING.md` - documentation update only

## Verification

Review the updated documentation for clarity and accuracy.
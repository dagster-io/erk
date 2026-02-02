---
title: Worktree Cleanup After Implementation
read_when:
  - implementing plans with .worker-impl/ folders
  - understanding when to clean up .worker-impl/
  - debugging plan implementation workflows
---

# Worktree Cleanup After Implementation

Plans implemented via remote agents create a `.worker-impl/` folder in the repository. This folder must be removed after implementation completes and CI passes, to prevent clutter in the main codebase.

## The .worker-impl/ Folder

### Purpose

When a plan is implemented by a remote agent (not locally via `/erk:plan-implement`):

- The agent creates a `.worker-impl/` folder containing plan metadata
- This folder tracks implementation state for the remote workflow
- It contains files like `plan.md`, `issue.json`, and session markers

### Why It Exists

The `.worker-impl/` folder serves two purposes during remote implementation:

1. **Workflow coordination**: Tracks which plan is being implemented
2. **Session linkage**: Connects implementation sessions to GitHub issues

### Why It Must Be Removed

After implementation completes:

- The `.worker-impl/` folder has no further purpose
- Keeping it pollutes the repository with workflow artifacts
- It can confuse future implementations (stale state)

## Cleanup Timing

Remove `.worker-impl/` after:

1. ✅ Implementation complete (all phases executed)
2. ✅ CI passes (tests, linting, type checking)
3. ✅ Ready to create or update PR

**Before:** Never remove during implementation (breaks workflow state)

## Cleanup Pattern

### Automated Cleanup (Preferred)

The `/erk:plan-implement` command handles cleanup automatically:

```bash
# After CI passes
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  git commit -m "Remove .worker-impl/ after implementation"
  git push
fi
```

This runs as part of Step 12 in the plan-implement workflow.

### Manual Cleanup (If Needed)

If automated cleanup didn't run:

```bash
# Remove the folder
git rm -rf .worker-impl/

# Commit the removal
git commit -m "Remove .worker-impl/ after implementation"

# Push to remote
git push
```

## Critical: Never Remove .impl/

**IMPORTANT**: The `.impl/` folder is for LOCAL implementations and must NEVER be removed automatically.

| Folder          | Purpose                    | Cleanup Timing               |
| --------------- | -------------------------- | ---------------------------- |
| `.impl/`        | Local plan implementation  | User reviews, manual cleanup |
| `.worker-impl/` | Remote plan implementation | Automatic after CI passes    |

**Why `.impl/` is preserved:**

- User may want to review plan vs actual implementation
- User may want to modify the plan for future reference
- Automatic removal would delete user's context

**Why `.worker-impl/` is removed:**

- Created by automated workflow, not user
- No review value (plan content is in GitHub issue)
- Serves no purpose after PR is open

## Cleanup Failures

### Symptom: .worker-impl/ Still Present After PR Created

**Likely causes:**

1. CI never passed (cleanup step was skipped)
2. Cleanup step failed (git rm error)
3. Manual implementation without running automated cleanup

**Fix:**

```bash
# Verify CI passed
gh pr checks

# If CI passed, remove manually
git rm -rf .worker-impl/
git commit -m "Remove .worker-impl/ after implementation"
git push
```

### Symptom: Multiple Implementation Folders

**Example:**

```
.impl/          # From local implementation
.worker-impl/   # From remote implementation
```

**Fix:**

Remove `.worker-impl/` only (never remove `.impl/`):

```bash
git rm -rf .worker-impl/
git commit -m "Remove .worker-impl/ after remote implementation"
git push
```

## Related Documentation

- [reliability-patterns.md](reliability-patterns.md) — Multi-layer cleanup enforcement
- `/erk:plan-implement` command — Automated cleanup workflow

# Plan: Auto-rename cmux workspace on worktree navigation

## Context

When navigating to a worktree, the cmux workspace name doesn't automatically update to reflect the current branch. This requires manually running `/local:cmux-workspace-rename` each time. Adding this to `.envrc` makes it automatic via direnv.

## Change

**File: `/Users/schrockn/code/erk/.envrc`**

Add after the existing `source_env_if_exists` line:

```bash
# Rename cmux workspace to current git branch
if command -v cmux &>/dev/null; then
  _branch=$(git branch --show-current 2>/dev/null)
  if [ -n "$_branch" ]; then
    cmux rename-workspace "$_branch" 2>/dev/null || true
  fi
  unset _branch
fi
```

Guards:
- `command -v cmux` — skip if cmux isn't installed
- `git branch --show-current` — get parameterized branch name
- `2>/dev/null || true` — fail silently (don't break activation if cmux errors)
- `unset _branch` — don't leak variables into the shell environment

## Verification

1. `cd` into a worktree → cmux workspace should rename to the branch
2. `cd` into root worktree → should rename to `master` (or current branch)
3. Without cmux installed → should silently skip

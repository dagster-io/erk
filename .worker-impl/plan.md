# Plan: Fix sync-divergence command documentation

## Problem

Step 5 incorrectly suggests using `gt restack --no-interactive` for Graphite workflows when resolving same-branch remote divergence.

**What we learned:**
- `gt restack` only rebases a branch onto its **parent branch** in the stack (e.g., rebasing feature onto master)
- `gt restack` does NOT handle when a branch has diverged from its **own remote tracking branch** (e.g., local `feature` vs `origin/feature`)
- For same-branch divergence, you must use `git rebase origin/$BRANCH` directly

## File to Modify

`/Users/schrockn/.erk/repos/erk/worktrees/erk-slot-22/.claude/commands/erk/sync-divergence.md`

## Changes

### 1. Fix Step 5 - Remove incorrect Graphite distinction

**Before:**
```markdown
5. **Execute rebase** (when both sides have commits):

   For Graphite workflows:

   ```bash
   gt restack --no-interactive
   ```

   For git-only workflows:

   ```bash
   git rebase origin/$BRANCH
   ```
```

**After:**
```markdown
5. **Execute rebase** (when both sides have commits):

   ```bash
   git rebase origin/$BRANCH
   ```

   > **Note:** Do not use `gt restack` here. Graphite's restack only handles parent branch relationships (rebasing onto the parent in your stack), not same-branch remote divergence.
```

### 2. Clarify the "Multiple branches in stack affected" edge case

The current text suggests `gt restack` handles this sync scenario - it doesn't. Should clarify this is about parent-child relationships after a sync.

**Before:**
```markdown
### Multiple branches in stack affected

If using Graphite with stacked PRs:

- `gt restack --no-interactive` handles the entire stack
- Conflicts may appear in multiple branches
- Resolve each in order (downstack to upstack)
```

**After:**
```markdown
### Multiple branches in stack affected

After syncing one branch, other branches in the stack may need rebasing onto their parents:

1. First: Sync the diverged branch using `git rebase origin/$BRANCH`
2. Then: Run `gt restack --no-interactive` to cascade changes through the stack
3. Conflicts may appear in multiple branches - resolve each in order (downstack to upstack)
```

## Verification

- Read the updated file to confirm changes are correct
- The documentation now accurately reflects that `git rebase origin/$BRANCH` is the correct approach for same-branch divergence
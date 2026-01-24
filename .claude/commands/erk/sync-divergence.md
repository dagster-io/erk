---
description: Sync branch with remote and resolve divergence intelligently
---

# Sync Divergence

Resolve "Branch X has been updated remotely" errors by syncing with remote and handling any resulting conflicts.

## Steps

1. **Fetch remote state**

   ```bash
   git fetch origin
   ```

2. **Get current branch name**

   ```bash
   BRANCH=$(git rev-parse --abbrev-ref HEAD)
   ```

3. **Diagnose divergence** - Understand what changed on each side:

   ```bash
   # Commits only on remote (what we need to incorporate)
   git log --oneline HEAD..origin/$BRANCH

   # Commits only on local (our work that might be lost)
   git log --oneline origin/$BRANCH..HEAD

   # Visual comparison of both
   git log --oneline --left-right --graph HEAD...origin/$BRANCH
   ```

4. **Analyze and decide:**

   | Remote-only commits | Local-only commits | Action                                             |
   | ------------------- | ------------------ | -------------------------------------------------- |
   | 0                   | 0                  | No divergence - just retry `gt submit`             |
   | 1+                  | 0                  | Fast-forward: `git merge --ff-only origin/$BRANCH` |
   | 0                   | 1+                 | Already ahead (shouldn't trigger this error)       |
   | 1+                  | 1+                 | **Rebase required** - continue to step 5           |

5. **Execute rebase** (when both sides have commits):

   ```bash
   git rebase origin/$BRANCH
   ```

   > **Note:** Do not use `gt restack` here. Graphite's restack only handles parent branch relationships (rebasing onto the parent in your stack), not same-branch remote divergence.

6. **If rebase causes conflicts:**

   <!-- Include shared conflict resolution steps -->

   @../../../.erk/docs/kits/erk/includes/conflict-resolution.md

7. **After successful sync:**
   - For Graphite: `gt submit` (or `gt ss`)
   - For git-only: `git push --force-with-lease`

8. **Verify completion** - Run `git status` and `git log --oneline -5` to confirm sync succeeded

## Edge Cases

### Remote has force-pushed (history rewritten)

If the commit SHAs don't match at all (not just diverged, but completely different):

- This indicates someone rewrote history on remote
- **Ask user** before proceeding - they may want to manually inspect
- Options: hard reset to remote (lose local), or carefully cherry-pick local commits

### Uncommitted local changes

If there are uncommitted changes when starting:

1. Stash changes: `git stash push -m "sync-divergence: uncommitted work"`
2. Perform sync
3. Pop stash: `git stash pop`
4. Handle any stash conflicts

### Multiple branches in stack affected

After syncing one branch, other branches in the stack may need rebasing onto their parents:

1. First: Sync the diverged branch using `git rebase origin/$BRANCH`
2. Then: Run `gt restack --no-interactive` to cascade changes through the stack
3. Conflicts may appear in multiple branches - resolve each in order (downstack to upstack)

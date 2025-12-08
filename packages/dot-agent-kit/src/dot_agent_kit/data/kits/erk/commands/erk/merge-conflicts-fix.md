---
description: Fix all merge conflicts and continue the git operation (rebase or cherry-pick)
---

# Fix Merge Conflicts

Fix all merge conflicts and continue the git operation (rebase or cherry-pick).

## Steps

1. **Check status** - Run `git status` to understand the state of the operation and identify conflicted files

2. **For each conflicted file:**

<!-- prettier-ignore -->
@../../docs/erk/includes/conflict-resolution.md

3. **After resolving all conflicts:**
   - If project memory includes a precommit check, run it and ensure no failures
   - Stage the resolved files with `git add`
   - Continue based on operation type:
     - If rebasing: `gt continue` (or `git rebase --continue`)
     - If cherry-picking: `git cherry-pick --continue`
     - Check `git status` output to determine which operation is in progress

4. **Loop** - If the operation continues with more conflicts, repeat the process

5. **Verify completion** - Check git status and recent commit history to confirm success

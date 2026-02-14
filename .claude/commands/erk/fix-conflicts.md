---
description: Fix all merge conflicts and continue the git rebase
---

# Fix Merge Conflicts

Fix all merge conflicts and continue the git rebase.

## Steps

1. **Check status** - Run `git status` to understand the state of the rebase and identify conflicted files

2. **For each conflicted file:**

For each conflicted file:

a. **Read the file** - Understand both sides of the conflict by examining the conflict markers:

- `<<<<<<< HEAD` marks the start of your local changes
- `=======` separates local from incoming changes
- `>>>>>>> <commit>` marks the end of incoming changes

b. **Understand intent** - Determine what each side was trying to accomplish:

- What was the local change trying to do?
- What was the remote change trying to do?
- Are they complementary or contradictory?

c. **Resolve intelligently:**

- If changes are complementary -> merge both
- If changes conflict semantically -> prefer the more recent/complete version
- If unclear -> ask the user for guidance

d. **Remove all conflict markers** - The resolved file should have no `<<<<<<<`, `=======`, or `>>>>>>>` markers

e. **Stage the resolution** - `git add <file>`

3. **After resolving all conflicts:**
   - If project memory includes a precommit check, run it and ensure no failures
   - Stage the resolved files with `git add`
   - Continue the rebase with `git rebase --continue`

4. **Loop** - If the rebase continues with more conflicts, repeat the process

5. **Verify completion** - Check git status and recent commit history to confirm success

6. **Push changes** - After rebase, the branch will have diverged from origin. Push the rebased branch:
   - For Graphite users: `gt submit` (or `gt ss`)
   - For git-only users: `git push --force-with-lease`

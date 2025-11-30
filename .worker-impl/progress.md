---
completed_steps: 0
total_steps: 25
---

# Progress Tracking

- [ ] 1. **Kit CLI Command** (`audit-branches.py`) - Python utility for reliable data gathering
- [ ] 2. **Slash Command** (`.claude/commands/erk/audit-branches.md`) - Claude workflow orchestration
- [ ] 1. **List branches:** Use `ctx.git.list_local_branches(repo_root)`
- [ ] 2. **Get PR status:** Use `ctx.github.get_prs_for_repo(repo_root, include_checks=False)` for batch efficiency
- [ ] 3. **Get commits ahead:** Use `git rev-list --count master..$branch`
- [ ] 4. **Get last non-merge commit:** Use `git log --no-merges -1 --format='%H|%ai|%s' $branch`
- [ ] 5. **Check worktree status:** Use `ctx.git.find_worktree_for_branch(repo_root, branch)`
- [ ] 1. **Safe to Delete** (no confirmation needed):
- [ ] 2. **Likely Stale** (confirm with user):
- [ ] 3. **May Be Superseded** (semantic analysis):
- [ ] 4. **Stale** (based on date):
- [ ] 5. **Keep** (do not suggest deletion):
- [ ] 1. Present the branches to clean up
- [ ] 2. Ask user to confirm (using AskUserQuestion or natural conversation)
- [ ] 3. On confirmation, execute cleanup:
- [ ] 4. Report results
- [ ] 1. Look at PR titles/commit messages
- [ ] 2. Compare with recent master commits
- [ ] 3. Identify if the work was done via a different branch
- [ ] 4. Present findings and ask user if they want to clean up
- [ ] 1. Test with no branches (only trunk)
- [ ] 2. Test with mixed branches (some merged, some open, some closed)
- [ ] 3. Test with stale branches
- [ ] 4. Test with branches in worktrees
- [ ] 5. Test error handling (git failures, github API failures)

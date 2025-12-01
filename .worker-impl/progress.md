---
completed_steps: 0
steps:
- completed: false
  text: 1. Current branch is master (or the trunk branch)
- completed: false
  text: 2. Working directory is clean (no uncommitted changes)
- completed: false
  text: '1. Get the current branch: `git branch --show-current`'
- completed: false
  text: '2. Get the trunk branch name: `git symbolic-ref refs/remotes/origin/HEAD
    | sed ''s@^refs/remotes/origin/@@''` (or use `git remote show origin | grep ''HEAD
    branch''`)'
- completed: false
  text: 3. Check if on trunk (current branch equals trunk branch)
- completed: false
  text: '4. If on trunk, check if working directory is clean: `git status --porcelain`'
- completed: false
  text: '5. If both conditions are met, run: `git pull --ff-only`'
- completed: false
  text: 6. Report success/skip reason to user
- completed: false
  text: 1. Search conversation for the last GitHub issue reference
- completed: false
  text: 2. Extract the issue number
- completed: false
  text: 3. **Sync trunk if on master/main with clean working directory** (NEW)
- completed: false
  text: 4. Run `erk submit <issue_number>` to trigger remote implementation
- completed: false
  text: 1. Get the current branch and trunk branch name
- completed: false
  text: '2. If current branch is the trunk branch (master or main):'
- completed: false
  text: 3. If not on trunk or working directory is dirty, skip this step silently
- completed: false
  text: '1. **Use `--ff-only`**: Prevents merge commits if local has diverged; fails
    cleanly'
- completed: false
  text: '2. **Non-blocking on pull failure**: If pull fails, continue with submit
    (the purpose is to get latest, not to block the workflow)'
- completed: false
  text: '3. **Silent skip when not applicable**: Don''t clutter output when not on
    trunk or dirty'
- completed: false
  text: '4. **Trunk detection**: Use git to detect trunk branch name dynamically (supports
    both `main` and `master`)'
total_steps: 19
---

# Progress Tracking

- [ ] 1. Current branch is master (or the trunk branch)
- [ ] 2. Working directory is clean (no uncommitted changes)
- [ ] 1. Get the current branch: `git branch --show-current`
- [ ] 2. Get the trunk branch name: `git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'` (or use `git remote show origin | grep 'HEAD branch'`)
- [ ] 3. Check if on trunk (current branch equals trunk branch)
- [ ] 4. If on trunk, check if working directory is clean: `git status --porcelain`
- [ ] 5. If both conditions are met, run: `git pull --ff-only`
- [ ] 6. Report success/skip reason to user
- [ ] 1. Search conversation for the last GitHub issue reference
- [ ] 2. Extract the issue number
- [ ] 3. **Sync trunk if on master/main with clean working directory** (NEW)
- [ ] 4. Run `erk submit <issue_number>` to trigger remote implementation
- [ ] 1. Get the current branch and trunk branch name
- [ ] 2. If current branch is the trunk branch (master or main):
- [ ] 3. If not on trunk or working directory is dirty, skip this step silently
- [ ] 1. **Use `--ff-only`**: Prevents merge commits if local has diverged; fails cleanly
- [ ] 2. **Non-blocking on pull failure**: If pull fails, continue with submit (the purpose is to get latest, not to block the workflow)
- [ ] 3. **Silent skip when not applicable**: Don't clutter output when not on trunk or dirty
- [ ] 4. **Trunk detection**: Use git to detect trunk branch name dynamically (supports both `main` and `master`)
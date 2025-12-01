---
completed_steps: 0
steps:
- completed: false
  text: 1. Implementation changes are staged (including any changes to `.worker-impl/progress.md`)
- completed: false
  text: 2. A commit is created with a message generated from `git diff --staged`
- completed: false
  text: 3. The diff analysis includes `.worker-impl/` files in the summary
- completed: false
  text: 4. Then `.worker-impl/` is deleted in a separate commit
- completed: false
  text: 5. The PR body (derived from commit message) still references `.worker-impl/`
- completed: false
  text: 1. Delete `.worker-impl/` folder FIRST
- completed: false
  text: 2. Stage all changes (both implementation + `.worker-impl/` deletion)
- completed: false
  text: 3. THEN generate the commit message from staged diff
- completed: false
  text: 4. Create a single atomic commit
- completed: false
  text: '1. Delete .worker-impl/ folder: `rm -rf .worker-impl/`'
- completed: false
  text: '2. Stage deletion: `git add .worker-impl/`'
- completed: false
  text: '3. Commit: `git commit -m "Clean up worker implementation artifacts after
    implementation"`'
- completed: false
  text: '4. Push: `git push`'
- completed: false
  text: '1. Delete .worker-impl/ folder FIRST: `rm -rf .worker-impl/`'
- completed: false
  text: '2. Stage ALL changes (implementation + folder deletion): `git add -A`'
- completed: false
  text: '3. Get the staged diff for commit message generation: `git diff --staged`'
- completed: false
  text: 4. Generate commit message from the diff (following diff-analysis-guide.md)
- completed: false
  text: 5. Create a single commit with the generated message
- completed: false
  text: '6. Push: `git push`'
- completed: false
  text: 1. DO NOT delete .impl/
- completed: false
  text: 2. DO NOT auto-commit
- completed: false
  text: 3. Leave changes for user review
- completed: false
  text: 1. Run `/erk:plan-implement` in a worktree with `.worker-impl/`
- completed: false
  text: 2. Verify the commit message does NOT reference `.worker-impl/` files
- completed: false
  text: 3. Verify the PR body does NOT reference `.worker-impl/` files
- completed: false
  text: 4. Verify only one implementation commit is created (not separate cleanup
    commit)
total_steps: 26
---

# Progress Tracking

- [ ] 1. Implementation changes are staged (including any changes to `.worker-impl/progress.md`)
- [ ] 2. A commit is created with a message generated from `git diff --staged`
- [ ] 3. The diff analysis includes `.worker-impl/` files in the summary
- [ ] 4. Then `.worker-impl/` is deleted in a separate commit
- [ ] 5. The PR body (derived from commit message) still references `.worker-impl/`
- [ ] 1. Delete `.worker-impl/` folder FIRST
- [ ] 2. Stage all changes (both implementation + `.worker-impl/` deletion)
- [ ] 3. THEN generate the commit message from staged diff
- [ ] 4. Create a single atomic commit
- [ ] 1. Delete .worker-impl/ folder: `rm -rf .worker-impl/`
- [ ] 2. Stage deletion: `git add .worker-impl/`
- [ ] 3. Commit: `git commit -m "Clean up worker implementation artifacts after implementation"`
- [ ] 4. Push: `git push`
- [ ] 1. Delete .worker-impl/ folder FIRST: `rm -rf .worker-impl/`
- [ ] 2. Stage ALL changes (implementation + folder deletion): `git add -A`
- [ ] 3. Get the staged diff for commit message generation: `git diff --staged`
- [ ] 4. Generate commit message from the diff (following diff-analysis-guide.md)
- [ ] 5. Create a single commit with the generated message
- [ ] 6. Push: `git push`
- [ ] 1. DO NOT delete .impl/
- [ ] 2. DO NOT auto-commit
- [ ] 3. Leave changes for user review
- [ ] 1. Run `/erk:plan-implement` in a worktree with `.worker-impl/`
- [ ] 2. Verify the commit message does NOT reference `.worker-impl/` files
- [ ] 3. Verify the PR body does NOT reference `.worker-impl/` files
- [ ] 4. Verify only one implementation commit is created (not separate cleanup commit)
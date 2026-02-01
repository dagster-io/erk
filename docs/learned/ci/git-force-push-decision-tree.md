---
title: Git Force Push Decision Tree
read_when:
  - "encountering 'git push' rejected with 'fetch first' error"
  - "dealing with divergent branches after rebase or squash"
  - "deciding whether force push is safe"
  - "debugging PR update workflows"
tripwire:
  trigger: "Before force pushing after git push rejection"
  action: "Read [Git Force Push Decision Tree](git-force-push-decision-tree.md) first. Check incoming commits with `git log HEAD..origin/branch`. Force push ONLY if no incoming commits exist. Unreviewed incoming commits cause permanent data loss."
---

# Git Force Push Decision Tree

When `git push` fails with "Updates were rejected because the remote contains work that you do not have locally," you need to decide: force push or pull first?

This document provides a decision tree to make that choice safely.

## The Problem

Git rejects non-fast-forward pushes by default to prevent data loss. However, some workflows intentionally create divergence (rebases, squashes, commit amendments), making force push the correct action.

**Key question**: Does the remote have commits you haven't reviewed?

## Decision Tree

```
git push fails with "fetch first"
    |
    v
Check outgoing commits:
git log origin/<branch>..HEAD
    |
    +---> No outgoing commits? -----> ERROR: Nothing to push, investigate
    |
    v
Check incoming commits:
git log HEAD..origin/<branch>
    |
    +---> Incoming commits exist? ---> PULL FIRST, review changes
    |
    +---> No incoming commits? ------> SAFE TO FORCE PUSH
```

## Commands

### 1. Check Outgoing Commits

```bash
git log origin/my-branch..HEAD
```

**Interpretation**:

- **Output present**: You have local commits not on remote (expected)
- **No output**: Nothing to push — something is wrong

### 2. Check Incoming Commits

```bash
git log HEAD..origin/my-branch
```

**Interpretation**:

- **No output**: Remote has no commits you lack — **safe to force push**
- **Output present**: Remote has commits you don't have — **pull and review first**

## When Force Push is Safe

Force push is safe when:

1. **Outgoing commits exist**: You have local work to push
2. **No incoming commits**: Remote has no commits you lack
3. **You created the divergence**: Via rebase, squash, or amend

**Example scenario**: After `gt submit` squashes your commits, the branch diverges from remote. You have the squashed commit locally, remote has the original multi-commit history. Incoming commits are empty (you already have the changes), so force push is safe.

## When Force Push is Dangerous

Force push is dangerous when:

1. **Incoming commits exist**: Remote has work you haven't reviewed
2. **Collaboration**: Others may have pushed to the branch
3. **Uncertainty**: You don't know why divergence occurred

**Risk**: Force pushing with unreviewed incoming commits causes **permanent data loss** of those commits.

## Common Scenarios

### Scenario 1: After Rebase

```bash
git rebase main
# Local history rewritten
git push
# Rejected: fetch first

git log HEAD..origin/my-branch
# Output: old commit history
git log origin/my-branch..HEAD
# Output: rebased commits

# Safe to force push (divergence is expected)
git push --force-with-lease
```

### Scenario 2: After Commit Squash

```bash
gt submit  # Squashes commits
# Now local has 1 commit, remote has 3 commits (pre-squash)
git push
# Rejected: fetch first

git log HEAD..origin/my-branch
# Output: 3 old commits (now squashed)
git log origin/my-branch..HEAD
# Output: 1 new squashed commit

# Safe to force push
git push --force-with-lease
```

### Scenario 3: Collaborator Pushed Changes

```bash
# You and teammate both work on feature branch
git push
# Rejected: fetch first

git log HEAD..origin/my-branch
# Output: commits from teammate

# NOT safe to force push — pull first
git pull
# Review teammate's changes, resolve conflicts if needed
git push
```

## Best Practices

### Use --force-with-lease

Always prefer `--force-with-lease` over `--force`:

```bash
git push --force-with-lease
```

**Why**: `--force-with-lease` fails if remote has commits you haven't fetched, preventing accidental overwrites even if your decision tree check was stale.

### Fetch Before Checking

Run `git fetch` before checking logs to ensure you're comparing against current remote state:

```bash
git fetch origin
git log HEAD..origin/my-branch
git log origin/my-branch..HEAD
```

### Document Expected Divergence

When workflows create expected divergence (like `gt submit`), document this in the command output:

```
Squashed 3 commits into 1. Branch will diverge from remote.
Run: git push --force-with-lease
```

## Tripwire

**Force pushing with unreviewed incoming commits causes data loss.**

There is no recovery mechanism if you force push over commits you haven't reviewed. The commits are permanently lost (unless someone else has them or they're in reflog).

Always check incoming commits before force pushing.

## Related Documentation

- [Commit Squash Divergence](commit-squash-divergence.md) - Expected divergence after `gt submit`
- [Git Rebase Workflow](../workflows/git-rebase.md) - Rebase creates expected divergence

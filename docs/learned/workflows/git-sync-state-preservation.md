---
title: Git Sync State Preservation
read_when:
  - "running gt sync or git rebase operations"
  - "preserving working tree changes during sync"
  - "debugging lost changes after a rebase"
tripwires:
  - action: "running gt sync without committing or stashing working tree changes"
    warning: "gt sync performs a rebase which can silently lose uncommitted changes. Always commit or stash before sync, and verify working tree state after."
---

# Git Sync State Preservation

`gt sync` performs a rebase operation that can silently lose uncommitted working tree changes. This document covers prevention and recovery.

## The Problem

When `gt sync` rebases your branch, any uncommitted changes in the working tree may be lost without warning. This includes:

- Unstaged modifications
- Staged but uncommitted changes
- New untracked files in directories affected by the rebase

## Prevention

Before running `gt sync` or any rebase operation:

1. **Commit**: `git commit -am "WIP: save state before sync"` — preferred for traceability
2. **Stash**: `git stash` — acceptable for quick saves
3. **Verify clean state**: `git status` should show no modifications

## Post-Sync Verification

After sync completes:

1. `git status` — verify working tree is clean (or has expected state)
2. `git log --oneline -5` — verify commit history looks correct
3. If changes were lost, check `git reflog` for recovery

## Recovery

If changes were lost during sync:

```bash
# Find the pre-sync state
git reflog

# Recover to a specific commit
git cherry-pick <commit-hash>
```

## Related Documentation

- [Graphite Stack Troubleshooting](../erk/graphite-stack-troubleshooting.md) — Common Graphite operation failures

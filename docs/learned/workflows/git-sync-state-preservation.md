---
title: Git Sync State Preservation
read_when:
  - "running gt sync or gt rebase during active development"
  - "working tree has uncommitted changes when syncing"
tripwires:
  - action: "running gt sync with uncommitted changes in the working tree"
    warning: "gt sync can rebase and create WIP commits that lose uncommitted working tree changes. Always commit or stash before sync, and verify git status after."
---

# Git Sync State Preservation

## The Problem

When running `gt sync` while the working tree has uncommitted changes, the sync operation may rebase commits and create WIP commits that do not preserve the working tree state. The result is that uncommitted edits are silently lost — no error message, no warning.

## When This Happens

This occurs specifically when:

1. Your branch has diverged from its remote tracking branch
2. You have uncommitted changes in the working tree
3. `gt sync` performs a rebase to reconcile the divergence

The rebase creates a clean commit state, and uncommitted changes that were in the working tree are not carried forward.

## Prevention

1. **Before sync:** Always commit or stash all working tree changes
2. **After sync:** Always run `git status` to verify the working tree state
3. **If changes are lost:** Re-apply edits from memory or from the reflog

## Related Documentation

- [Agent Orchestration Safety](../planning/agent-orchestration-safety.md) — Verification patterns between pipeline steps

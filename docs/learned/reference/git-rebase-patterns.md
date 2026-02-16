---
title: Git Rebase Patterns
read_when:
  - "rebasing after erk pr submit"
  - "seeing 'skipped previously applied commit' warnings"
---

# Git Rebase Cherry-Pick Skip Behavior

When rebasing after `erk pr submit` has created a remote commit, git automatically skips local commits that are already applied to the remote.

## The Message

```
skipped previously applied commit abc1234
hint: use --reapply-cherry-picks to include skipped commits
```

## This is Normal

The remote "WIP: Prepare for PR submission" commit often contains the same changes as your local commit. Git detects this and skips the duplicate.

## No Action Required

This is informational. The rebase completes successfully with no manual intervention needed.

---
title: Commit Squash Divergence
read_when:
  - "encountering 'fetch first' after gt submit"
  - "dealing with divergent branches after Graphite operations"
  - "understanding expected vs unexpected branch divergence"
  - "working with Graphite PR submission workflow"
---

# Commit Squash Divergence

After `gt submit` squashes commits, the local branch diverges from the remote — this is **expected behavior**, not an error. Understanding this prevents incorrect responses to the resulting `git push` failure.

## What Happens

### Before `gt submit`

```
Local:  A - B - C - D
Remote: A - B - C - D
```

Branch is in sync with remote.

### After `gt submit`

```
Local:  A - B - C - D'  (D' = squashed commit)
Remote: A - B - C - D   (original commits)
```

**Divergence created**:

- Local has D' (new squashed commit)
- Remote has D (original pre-squash commit)
- Histories have diverged at commit C

### Attempting `git push`

```bash
git push
# To github.com:owner/repo.git
#  ! [rejected]        my-branch -> my-branch (fetch first)
# error: failed to push some refs to 'github.com:owner/repo.git'
# hint: Updates were rejected because the remote contains work that you do
# hint: not have locally. This is usually caused by another repository pushing
# hint: to the same ref. You may want to first integrate the remote changes
# hint: (e.g., 'git pull ...') before pushing again.
```

**This is NOT an error** — it's expected divergence from squashing.

## Why Divergence is Expected

`gt submit` rewrites history by squashing multiple commits into one. This creates a new commit (D') that replaces the original commits (D). The remote still has the original history.

**Key insight**: The divergence is **intentional**, not a conflict. Local and remote don't have conflicting changes — they have the same changes in different commit structures.

## Correct Response

Use force push:

```bash
git push --force-with-lease
```

**Why force push is safe**:

1. You created the divergence via `gt submit`
2. No incoming commits from others: `git log HEAD..origin/branch` is empty
3. Remote commits are superseded by local squashed commit

See [Git Force Push Decision Tree](git-force-push-decision-tree.md) for the full decision framework.

## Verification

Before force pushing, verify no unreviewed incoming commits:

```bash
git log HEAD..origin/my-branch
```

**Expected output**: The original pre-squash commits (now superseded)

**If output shows unexpected commits**: Someone else pushed to the branch — pull and review before force pushing.

## Common Mistake: Pulling Instead of Force Pushing

**Wrong response**:

```bash
git pull  # Creates merge commit, undoing the squash
```

**Result**:

- Merge commit combines squashed commit (D') with original commits (D)
- Now you have BOTH the original and squashed commits in history
- PR shows duplicate changes
- Squash operation effectively undone

**Right response**:

```bash
git push --force-with-lease  # Replaces remote history with squashed version
```

## Automated Workflow

The Graphite workflow could provide clearer guidance:

```bash
gt submit
# Output should include:
# Squashed 3 commits into 1.
# Branch will diverge from remote (expected).
# Run: git push --force-with-lease
```

This explicit instruction prevents confusion and incorrect responses.

## Related Documentation

- [Git Force Push Decision Tree](git-force-push-decision-tree.md) - General framework for force push decisions
- [Graphite Workflow](../workflows/graphite.md) - Full Graphite stack management

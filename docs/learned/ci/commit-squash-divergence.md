---
title: Commit Squash Divergence
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
read_when:
  - "encountering 'fetch first' after gt submit"
  - "dealing with divergent branches after Graphite operations"
  - "understanding expected vs unexpected branch divergence"
  - "working with Graphite PR submission workflow"
tripwire:
  trigger: "After `gt submit`, git push fails with 'fetch first'"
  action: "Read [Commit Squash Divergence](commit-squash-divergence.md). This is EXPECTED behavior from history rewriting. Force push with `git push --force-with-lease` after verifying no incoming commits."
---

# Commit Squash Divergence

After `gt submit` squashes commits, `git push` fails with "fetch first" — this is **expected behavior**, not an error to fix. Understanding why prevents incorrect responses that undo the squash.

## Why Divergence is Expected After Squashing

History-rewriting operations (rebase, squash, amend) create new commit objects with different SHA-1 hashes. The remote still has the old commit objects. Git sees these as divergent histories, not as "same changes in different form."

**The key insight**: Squashing creates _intentional_ divergence. The remote hasn't changed (no collaboration happened) — your local branch changed. The failure is git's safety mechanism against unintentional overwrites, not a signal that something went wrong.

## The Critical Mistake: Pulling After Squashing

When git says "fetch first," the intuitive response is to pull. **This is wrong for squash workflows**.

Pulling merges the remote's pre-squash commits with your local squashed commit, creating a merge commit that includes both versions. The result:

- All commits appear twice in history (once as originals, once in squashed form)
- PR shows duplicate changes
- The squash operation is effectively undone

**Why this happens**: `git pull` is `git fetch` + `git merge`. The merge creates a new commit with both parents: your squashed commit and the remote's pre-squash commits. Git doesn't understand that these represent the same logical changes.

## Correct Response: Force Push

After verifying no incoming commits exist, force push replaces the remote history:

```bash
git log HEAD..origin/my-branch  # Should show only your pre-squash commits
git push --force-with-lease
```

**Why `--force-with-lease` is safe here**:

1. You created the divergence via `gt submit`
2. The "incoming commits" are your own pre-squash commits (already incorporated in the squashed version)
3. No collaboration has occurred on the branch since you last fetched

See [Git Force Push Decision Tree](git-force-push-decision-tree.md) for the general decision framework and safety checks.

## Workflow Gap: Missing Guidance

The confusion arises because `gt submit` doesn't explicitly state that divergence is expected:

```bash
gt submit
# Squashes and rebases, then exits silently

git push
# Error: Updates were rejected (fetch first)
```

An agent seeing "fetch first" after squashing may not recognize this as expected. The error message suggests pulling, which is the wrong action.

**Better workflow**: `gt submit` could detect that the branch is published and suggest the next action:

```
✓ Squashed 3 commits into 1
⚠ Branch will diverge from remote (expected after squashing)
→ Run: git push --force-with-lease
```

This explicit guidance prevents the pull-after-squash mistake.

## Decision Rule

After any history-rewriting operation (rebase, squash, amend):

1. **Expected**: `git push` fails with "fetch first"
2. **Check incoming commits**: `git log HEAD..origin/branch` should show only your own pre-rewrite commits
3. **If confirmed**: Force push to replace remote history
4. **If unexpected commits appear**: Someone else pushed — pull and investigate before force pushing

The distinction: Expected incoming commits (your own pre-rewrite work) vs unexpected incoming commits (collaboration you haven't seen).

## Related Documentation

- [Git Force Push Decision Tree](git-force-push-decision-tree.md) - General framework for force push decisions with detailed command examples

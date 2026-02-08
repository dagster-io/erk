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

## The Core Question

When `git push` fails with "Updates were rejected because the remote contains work that you do not have locally," the critical question is: **Does the remote have commits you haven't reviewed?**

Git's rejection is a safety mechanism against data loss. But some workflows (rebase, squash, amend) intentionally rewrite history, making force push the correct response. The decision tree below prevents confusing intentional divergence with collaboration conflicts.

## Why This Matters

**The intuitive response to "fetch first" is wrong for history-rewriting workflows.** Pulling after a squash merges your squashed commit with the remote's pre-squash commits, creating duplicates of every change. The squash is effectively undone.

Understanding when divergence is expected vs unexpected prevents this mistake. See [Commit Squash Divergence](commit-squash-divergence.md) for the detailed failure mode when agents pull after squashing.

## The Decision Tree

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

## The Safety Check Commands

These two `git log` invocations distinguish expected from unexpected divergence:

### 1. Outgoing commits (what you're pushing)

```bash
git log origin/my-branch..HEAD
```

- **Output present**: You have local commits to push (expected)
- **No output**: Nothing to push — investigate why push was attempted

### 2. Incoming commits (what remote has that you lack)

```bash
git log HEAD..origin/my-branch
```

- **No output**: Remote has nothing you lack — **safe to force push**
- **Output present**: Remote has commits you haven't reviewed — **pull and review first**

**Why this works**: After a squash, incoming commits show your own pre-squash history. You already have those changes (now squashed), so force push is safe. But if a collaborator pushed, incoming commits show their work — force pushing would delete it.

## When Force Push is Safe

Three conditions must all be true:

1. **You have outgoing commits**: Local work exists to push
2. **No unreviewed incoming commits**: Remote has nothing you lack, or only has your own pre-rewrite history
3. **You know why divergence occurred**: Rebase, squash, or amend operation

**Common safe scenario**: After `gt submit` squashes 3 commits into 1, the branch diverges. Incoming commits show the 3 old commits (now squashed). You already have the changes, so force push replaces remote history with the squashed version.

## When Force Push is Dangerous

Force push causes permanent data loss when:

1. **Incoming commits exist from collaborators**: Someone else pushed work you haven't seen
2. **You don't know why divergence occurred**: Unexpected state requires investigation
3. **Collaborative branch**: Multiple people pushing to the same branch

**The risk**: Force pushing over unreviewed incoming commits is irrecoverable. Those commits are lost unless someone else has them or they're in reflog (which expires).

## Implementation Gap: --force vs --force-with-lease

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/remote_ops/real.py, RealGitRemoteOps.push_to_remote -->

Erk currently uses `--force` when the force flag is true (see `RealGitRemoteOps.push_to_remote()` in `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/real.py`). This is less safe than `--force-with-lease`.

**Why `--force-with-lease` is better**: It fails if the remote has commits you haven't fetched yet, even if your decision tree check passed. This prevents race conditions where someone pushes between your check and your push.

Manual force pushes should always use:

```bash
git push --force-with-lease
```

## Best Practice: Fetch Before Checking

Always fetch before running the decision tree commands:

```bash
git fetch origin
git log HEAD..origin/my-branch
git log origin/my-branch..HEAD
```

This ensures you're comparing against current remote state, not stale tracking refs.

## Workflow Documentation Gap

History-rewriting operations should document that divergence is expected:

```
✓ Squashed 3 commits into 1
⚠ Branch will diverge from remote (expected after squashing)
→ Next: git push --force-with-lease
```

Without this explicit guidance, agents seeing "fetch first" may not recognize it as expected behavior. The error message suggests pulling, which is the wrong action for squash workflows.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _core_submit_flow -->

The submit pipeline (see `_core_submit_flow()` in `src/erk/cli/commands/pr/submit_pipeline.py`) handles divergence by auto-rebasing if behind, then using the force flag for pushes. This prevents the pull-after-squash mistake, but doesn't expose the decision tree to users who manually push.

## Related Documentation

- [Commit Squash Divergence](commit-squash-divergence.md) - Why pulling after squashing duplicates changes

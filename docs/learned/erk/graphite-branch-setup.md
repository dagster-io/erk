---
title: Graphite Branch Setup Before PR Submission
read_when:
  - "submitting a PR with Graphite"
  - "encountering no_parent error"
  - "setting up branch tracking for gt"
---

# Graphite Branch Setup Before PR Submission

When using erk worktrees with Graphite, branches must be tracked in Graphite before submitting PRs.

## The Problem

Erk creates git branches and worktrees, but does not automatically register them with Graphite. When you try to submit a PR with `gt submit`, you may encounter:

```
error: no_parent - Branch 'feature-branch' is not tracked by Graphite
```

## The Solution

Before submitting a PR, track the branch in Graphite:

```bash
gt track --parent master
```

This tells Graphite:

1. This branch should be managed by Graphite
2. The parent branch is `master` (or `main` if that's your trunk)

## Verification

Check that your branch is properly tracked:

```bash
gt ls
```

You should see your branch in the stack output with its parent relationship.

## Typical Workflow

1. **Create worktree with erk:**

   ```bash
   erk wt create feature-branch
   ```

2. **Navigate to worktree:**

   ```bash
   erk br co feature-branch
   ```

3. **Make changes and commit:**

   ```bash
   git add .
   git commit -m "Implement feature"
   ```

4. **Track branch in Graphite:**

   ```bash
   gt track --parent master
   ```

5. **Submit PR:**
   ```bash
   gt submit
   ```

## Common Errors

### no_parent Error

**Message:** `error: no_parent - Branch 'X' is not tracked by Graphite`

**Cause:** Branch was created outside Graphite (e.g., by erk or plain git)

**Fix:** `gt track --parent <trunk-branch>`

### Wrong Parent

**Message:** PR shows wrong base branch

**Cause:** Branch was tracked with incorrect parent

**Fix:**

```bash
gt track --parent <correct-parent>
gt restack
```

## Related Topics

- Load `gt-graphite` skill for comprehensive Graphite guidance
- [Branch Cleanup](branch-cleanup.md) - Cleaning up branches and worktrees

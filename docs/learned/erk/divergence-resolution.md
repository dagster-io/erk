---
title: Divergence Resolution Patterns
read_when:
  - encountering git push rejection
  - handling remote branch divergence
  - working with /erk:pr-address workflow
  - resolving non-fast-forward errors
tripwires: []
---

# Divergence Resolution Patterns

## The Problem

When working with automated PR workflows (like `/erk:pr-address`), remote branches often diverge from local state. Automated systems may add commits during workflows:

- "WIP: Prepare..." commits from preparation scripts
- CI formatting commits (Prettier, ruff)
- Bot changes (dependency updates, automated fixes)

This causes git push rejections with "non-fast-forward" errors.

## Two Types of Divergence

### Same-Branch Divergence

When the **same branch** has commits on remote that aren't in local:

```bash
# Example: origin/feature-branch has commits not in local feature-branch
error: failed to push some refs to 'origin'
hint: Updates were rejected because the remote contains work that you do not have locally
```

**Resolution**: Use `git rebase` (NOT `gt restack`)

```bash
git fetch origin
git status  # Verify which branch you're on
git rebase origin/feature-branch
git push --force-with-lease
```

### Stack Divergence

When branches in your **stack** have changed relative to each other:

```bash
# Example: Your stack's parent branch moved, affecting child branches
```

**Resolution**: Use `gt restack`

```bash
gt restack
git push --force-with-lease
```

## Key Distinction

- **Same-branch divergence** = Use `git rebase origin/$BRANCH`
- **Stack divergence** = Use `gt restack`

Don't use `gt restack` for same-branch divergence - it's designed for stack relationships, not remote synchronization.

## Standard Resolution Workflow

When you encounter a push rejection during PR workflows:

1. **Fetch latest remote state**:

   ```bash
   git fetch origin
   ```

2. **Check current status**:

   ```bash
   git status
   ```

3. **Identify divergence type**:
   - If output shows "Your branch and 'origin/X' have diverged" → Same-branch divergence
   - If stack relationships are broken → Stack divergence

4. **Apply appropriate resolution**:

   ```bash
   # For same-branch divergence:
   git rebase origin/$(git branch --show-current)

   # For stack divergence:
   gt restack
   ```

5. **Force push with safety**:
   ```bash
   git push --force-with-lease
   ```

## Real Example

During `/erk:pr-address` execution:

1. Agent makes local changes and commits
2. Tries to push
3. Push rejected: remote has "WIP: Prepare for PR submission" commit
4. Resolution:
   ```bash
   git fetch origin
   git rebase origin/feature-branch
   git push --force-with-lease
   ```

## Why This Matters

Automated PR workflows intentionally add commits (preparation, formatting, markers). This is expected behavior, not an error. Understanding the distinction between same-branch and stack divergence ensures you use the right tool for resolution.

## Prevention

You can't prevent divergence in managed workflows - it's by design. Instead:

- **Expect it**: Always `git fetch` before pushing in PR workflows
- **Recognize it quickly**: Learn to identify divergence type from git output
- **Resolve confidently**: Use the appropriate tool (rebase vs restack)

## Related Documentation

- [PR Address Workflows](pr-address-workflows.md) - Complete PR feedback workflow
- [Graphite Branch Setup](graphite-branch-setup.md) - Stack management basics

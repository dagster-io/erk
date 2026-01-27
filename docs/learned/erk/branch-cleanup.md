---
title: Branch Cleanup Guide
read_when:
  - "cleaning up branches"
  - "removing dormant worktrees"
  - "managing branch lifecycle"
---

# Branch Cleanup Guide

This guide documents the process for identifying and cleaning up dormant local branches, including those tracked by Graphite and those with associated worktrees.

## Overview

When working with erk, you accumulate:

- **Git branches** - Local branches from feature work
- **Graphite stacks** - Branches tracked by `gt` for PR management
- **Worktrees** - Separate working directories for parallel development

All three need coordinated cleanup. Deleting a branch that has a worktree will fail. Deleting a gt-tracked branch with `git branch -d` leaves orphaned metadata.

## Step 1: Analyze Branch Staleness

### List branches by author date (excludes rebases)

Rebases update committer date but not author date. Use author date for true activity:

```bash
branches_file=$(mktemp)
git branch --format='%(refname:short)' | grep -v '^master$' > "$branches_file"
while IFS= read -r branch; do
  base=$(git merge-base master "$branch" 2>/dev/null)
  if [ -n "$base" ]; then
    commits_ahead=$(git rev-list --count "$base".."$branch" 2>/dev/null)
    last_author_date=$(git log --format='%ai' --author-date-order -1 "$branch" 2>/dev/null)
    last_author_relative=$(git log --format='%ar' --author-date-order -1 "$branch" 2>/dev/null)
    echo "$last_author_date|$branch|$commits_ahead|$last_author_relative"
  fi
done < "$branches_file" | sort
rm "$branches_file"
```

Output columns: `date | branch | commits_ahead | relative_time`

### Identify merged branches

```bash
git branch --merged master | grep -v '^\*' | grep -v 'master'
```

Merged branches with 0 commits ahead are safe to delete.

### Check which branches have worktrees

```bash
git worktree list
```

### Check which branches are tracked by Graphite

```bash
gt ls
```

## Step 2: Cleanup Order

**Critical**: Follow this order to avoid errors:

1. **Remove worktrees first** (if any)
2. **Delete branches via `gt delete`** (for gt-tracked branches)
3. **Delete remaining branches via `git branch -D`** (for untracked branches)

### Remove worktrees

```bash
git worktree remove --force "/path/to/worktree"
```

Or for multiple:

```bash
git worktree remove --force "/Users/you/.erk/repos/repo/worktrees/branch-name"
```

### Delete gt-tracked branches

Use `gt delete` to clean up both the branch and Graphite metadata:

```bash
gt delete --force branch-name
```

**Note**: `gt delete` only accepts one branch at a time.

For multiple branches:

```bash
for branch in branch1 branch2 branch3; do
  gt delete --force "$branch"
done
```

### Delete non-gt branches

For branches not tracked by Graphite:

```bash
git branch -D branch-name
```

## Step 3: Verify Cleanup

```bash
# Check remaining branches
git branch

# Check remaining worktrees
git worktree list

# Check Graphite state
gt ls
```

## Worktree State After Landing PRs

When `erk land` completes, it deletes the feature branch and attempts to checkout trunk (master). However, this checkout may fail if trunk is already checked out in another worktree.

### Expected Behavior Table

| Worktree Type   | Trunk Available | Result               |
| --------------- | --------------- | -------------------- |
| Root worktree   | Always          | Checked out on trunk |
| Linked worktree | Yes             | Checked out on trunk |
| Linked worktree | No (held)       | Detached HEAD state  |

### Why Checkout May Fail

Git enforces a single-checkout constraint: a branch can only be checked out in one worktree at a time. When landing from a linked worktree while the root worktree holds trunk, the post-land checkout fails silently, leaving the worktree in detached HEAD state.

### Recovering from Detached HEAD

When a worktree is left in detached HEAD after landing:

```bash
# Check current state
git status  # Shows "HEAD detached at ..."

# Option 1: Checkout any available branch
git checkout other-feature-branch

# Option 2: Create a new branch for new work
git checkout -b new-feature

# Option 3: Navigate to root worktree for trunk operations
cd /path/to/root/worktree
git checkout master
```

This is expected behavior, not an error. The PR was successfully landed; only the post-land navigation was skipped.

## Common Errors and Solutions

### "branch is currently checked out in another worktree"

The branch has a worktree. Remove it first:

```bash
git worktree list | grep branch-name  # Find the worktree path
git worktree remove --force /path/to/worktree
```

### "Cannot perform this operation on untracked branch"

The branch isn't tracked by Graphite. Use git directly:

```bash
git branch -D branch-name
```

### Branch shows as merged but has commits ahead

The branch was likely rebased after merging. Check if the commits exist in master:

```bash
git log master --oneline | grep "commit message keywords"
```

If the work is in master, safe to delete with `-D`.

## Dormancy Indicators

Use these signals to prioritize cleanup:

| Signal                      | Meaning                                   |
| --------------------------- | ----------------------------------------- |
| 0 commits ahead + merged    | Safe to delete                            |
| No diff from master         | Already merged (even if git doesn't know) |
| 7+ days since author date   | Likely abandoned                          |
| Has worktree but merged     | Forgot to clean up                        |
| "cp" or WIP commit messages | Incomplete work, review before deleting   |

## Quick Cleanup Script

For batch cleanup of merged branches with worktrees:

```bash
# 1. Get merged branches
MERGED=$(git branch --merged master | grep -v '^\*' | grep -v 'master' | sed 's/^[+ ]*//')

# 2. For each, remove worktree if exists, then delete
for branch in $MERGED; do
  # Check for worktree
  wt_path=$(git worktree list | grep "\[$branch\]" | awk '{print $1}')
  if [ -n "$wt_path" ]; then
    echo "Removing worktree: $wt_path"
    git worktree remove --force "$wt_path"
  fi

  # Delete branch (try gt first, fall back to git)
  echo "Deleting branch: $branch"
  gt delete --force "$branch" 2>/dev/null || git branch -D "$branch"
done
```

## See Also

- [Architecture](../architecture/) - Worktree management in erk
- [Planning](../planning/) - Plan-based development workflow
- Load `gt-graphite` skill for Graphite stack management

---
description: Audit and clean up stale branches, worktrees, and PRs
---

# /audit-branches

Automates the branch audit workflow to identify stale branches, worktrees, and PRs that should be cleaned up.

## Usage

```bash
/audit-branches
```

## What This Command Does

1. **Collects data** about PRs, worktrees, and branches
2. **Analyzes staleness** based on context (not just age)
3. **Presents categorized recommendations** for cleanup
4. **Allows user selection** of what to clean
5. **Executes cleanup** with confirmation before destructive operations

---

## Agent Instructions

You are executing a branch audit workflow. Follow these phases carefully.

### Phase 1: Data Collection

Collect comprehensive data about the repository state. Run these commands to gather information:

**1.1 Get all PRs (open and closed):**

```bash
gh pr list --state all --limit 100 --json number,title,state,headRefName,updatedAt,mergeable,isDraft
```

**1.2 List all worktrees:**

```bash
git worktree list
```

**1.3 Get all local branches:**

```bash
git branch --format='%(refname:short)'
```

**1.4 Get all remote branches:**

```bash
git branch -r --format='%(refname:short)' | grep -v HEAD
```

**1.5 Get recent commit info for each branch (batch by 10):**
For each branch, get the last commit:

```bash
git log -1 --format="%h %s (%cr)" origin/<branch> 2>/dev/null || echo "no remote"
```

**1.6 Identify local-only branches:**
Branches that exist locally but have no remote tracking branch.

**1.7 Detect worktree anomalies:**

- **Duplicate worktrees**: Multiple worktrees at same commit
- **Branch mismatches**: Worktree directory name doesn't match checked-out branch

### Phase 2: Analysis

**IMPORTANT: Staleness is context-based, NOT age-based.**

Age > 2 weeks is a soft signal to investigate, but NOT an automatic reason to close.

Analyze each branch/PR for these staleness indicators:

**Context-Based Staleness Criteria:**

1. **Superseded** - A newer PR exists for the same feature
   - Look for PRs with similar titles/prefixes
   - Check if one PR was created after another for same functionality

2. **Duplicate** - Same issue number prefix, multiple attempts
   - Look for branches like `123-feature-v1`, `123-feature-v2`
   - Identify which is the current attempt vs abandoned

3. **Abandoned WIP** - Only contains "WIP" or checkpoint commits
   - Check commit messages for "WIP", "cp", "checkpoint", "tmp"
   - No substantive implementation commits

4. **Outdated design docs** - Design doc PRs for already-implemented features
   - Check if the feature mentioned has since been merged

5. **Feature pivoted** - Implementation took a different approach
   - Look for similar features implemented differently

6. **Massively diverged** - Branch far behind master but may contain valuable ideas
   - Assess rebase difficulty: `git rebase master --dry-run` or attempt rebase to see conflicts
   - If merge conflicts would be extensive or complex to resolve:
     - The _code_ is stale and impractical to rebase
     - But the _thesis_ (feature idea, approach) may still be valuable
   - **Recommendation**: Extract the core idea and reimplement on current master
     - Summarize what the branch was trying to accomplish
     - Create a new issue/branch to implement the same feature cleanly
     - Close the stale PR with a note about the reimplementation plan

7. **Feature merged differently** - Work exists in master via different PR
   - For branches with substantive commits, search master: `git log --grep="<feature keyword>" master`
   - If similar feature exists, branch is superseded even if PR wasn't merged

### Phase 2.5: No-PR Worktree Analysis

For worktrees without associated PRs:

**2.5.1 Get unique commits:**

```bash
git log master..HEAD --oneline  # from worktree directory
```

**2.5.2 Analyze actual code content:**

- **Empty** (0 unique commits) → Safe to delete
- **Has commits** → Examine the actual code changes:
  - `git diff master --stat` to see scope
  - `git log master..HEAD -p -- '*.py'` to see implementation
  - Determine: What feature/fix does this implement?
  - Check if that feature exists in master via different implementation

### Phase 2.7: Deep Content Analysis (for uncertain branches)

For branches that aren't clearly stale or clearly valuable:

1. **View actual code changes**: `git log master..HEAD -p -- '*.py'`
2. **Identify the thesis**: What feature/improvement was this trying to implement?
3. **Check if feature exists in master**: Search for key function/class names
4. **Assess value**: Is the idea worth reimplementing even if code is stale?

### Phase 3: Categorization

Present branches/PRs in these categories:

**🔴 SHOULD CLOSE** - PRs that should be closed

- Include context-based reason for each (superseded, duplicate, abandoned, etc.)
- NOT just "old" - must have a specific reason

**🟡 CLEANUP** - Branches to delete

- MERGED PRs (safe to delete)
- CLOSED PRs (safe to delete)
- Local-only branches with no work
- Orphaned worktrees

**🟢 CONSIDER MERGING** - PRs worth attention

- MERGEABLE status (no conflicts)
- Contains substantive work
- Recent activity or nearly complete

**🔵 NEEDS ATTENTION** - PRs requiring manual review

- CONFLICTING status (needs rebase)
- Draft PRs with significant work
- Unclear status

### Phase 4: Present Findings

Present the analysis in tables for each category:

```markdown
## 🔴 SHOULD CLOSE (X PRs)

| PR   | Title     | Reason             | Last Updated |
| ---- | --------- | ------------------ | ------------ |
| #123 | Feature X | Superseded by #456 | 3 weeks ago  |

## 🟡 CLEANUP (X branches)

| Branch      | Type       | Status         |
| ----------- | ---------- | -------------- |
| feature-old | Merged PR  | Safe to delete |
| local-test  | Local only | No remote      |

## 🟢 CONSIDER MERGING (X PRs)

| PR   | Title       | Status    | Action Needed  |
| ---- | ----------- | --------- | -------------- |
| #789 | New Feature | Mergeable | Review & merge |

## 🔵 NEEDS ATTENTION (X PRs)

| PR   | Title       | Issue       | Recommendation |
| ---- | ----------- | ----------- | -------------- |
| #101 | WIP Feature | Conflicting | Rebase needed  |
```

### Phase 5: User Interaction

After presenting findings, ask the user what they want to do:

**Use AskUserQuestion tool to get user selection:**

Ask which categories to act on:

- "Close all 🔴 SHOULD CLOSE PRs"
- "Delete all 🟡 CLEANUP branches"
- "Review 🟢 CONSIDER MERGING individually"
- "Skip cleanup for now"

Allow user to exclude specific branches/PRs by number if needed.

### Phase 6: Execution

**IMPORTANT: Confirm before each destructive operation type.**

Execute in this order:

**6.1 Close PRs (if selected):**

```bash
gh pr close <number> --comment "Closing as part of branch audit: <reason>"
```

**6.2 Remove worktrees (if applicable):**

```bash
git worktree remove --force <path>
```

**6.3 Delete local branches (batched):**

```bash
git branch -D <branch1> <branch2> ...
```

**6.4 Delete remote branches (batched):**

```bash
git push origin --delete <branch1> <branch2> ...
```

**6.5 Prune worktrees:**

```bash
git worktree prune
```

### Phase 7: Summary

After execution, provide a summary:

```markdown
## Audit Complete

**Actions Taken:**

- Closed X PRs
- Removed X worktrees
- Deleted X local branches
- Deleted X remote branches

**Remaining:**

- X PRs need attention (🔵)
- X PRs ready to merge (🟢)
```

## Key Principles

1. **No fixed age threshold** - 2 weeks is a soft signal only
2. **Context matters** - Always provide a reason beyond "old"
3. **User confirms** - Never delete without explicit confirmation
4. **Batch operations** - Group similar operations for efficiency
5. **Safe ordering** - Close PRs before deleting branches

## Error Handling

- If a branch deletion fails, continue with others and report failures at end
- If PR close fails, note it and continue
- Always run `git worktree prune` at the end regardless of other operations

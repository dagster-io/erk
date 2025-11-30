---
description: Audit git branches for cleanup candidates
---

# /erk:audit-branches

Audit all local git branches to identify cleanup candidates.

## Usage

```bash
/erk:audit-branches
```

## Workflow

### Step 1: Gather Branch Data

Run the kit CLI command to gather branch metadata:

```bash
dot-agent run erk audit-branches
```

This outputs JSON with:
- Branch names
- Commits ahead of trunk
- PR status (OPEN/CLOSED/MERGED/NONE)
- Last non-merge commit date
- Worktree status

Parse the JSON output to analyze branches.

### Step 2: Categorize Branches

Group branches into cleanup categories:

1. **Safe to Delete** (recommend deletion):
   - Branches with PRs that are MERGED
   - Empty branches (0 commits ahead) without open PRs

2. **Likely Stale** (confirm with user):
   - Branches with PRs that are CLOSED (not merged)
   - Branches with no PR and last commit older than 30 days

3. **May Be Superseded** (semantic analysis):
   - Compare branch purpose (from PR title/commit message) with recent trunk commits
   - Identify if similar work was done via different branch

4. **Active** (do not suggest deletion):
   - Open PRs
   - Recent activity (last commit within 30 days)
   - Trunk branch
   - Branches checked out in worktrees

### Step 3: Present Findings

Present a summary table:

```
## Branch Audit Results

| Category | Count |
|----------|-------|
| Safe to Delete (merged/empty) | N |
| Closed PRs | N |
| Stale (>30 days) | N |
| Active (keep) | N |
```

For each category except "Active", list branches with details:

**Safe to Delete:**
- `branch-name`: PR #123 MERGED
- `other-branch`: 0 commits ahead, no PR

**Closed PRs:**
- `branch-name`: PR #456 CLOSED "Feature title" (5 commits ahead)

**Stale (>30 days):**
- `branch-name`: Last commit 45 days ago, no PR

### Step 4: Interactive Cleanup

For each cleanup category (starting with safest):

1. Present the branches to clean up
2. Ask user to confirm cleanup
3. On confirmation, execute cleanup:

```bash
# If branch is checked out in worktree, remove worktree first
git worktree remove --force /path/to/worktree

# Delete branch
git branch -D branch-name
```

4. Report results

### Step 5: Semantic Analysis (Optional)

For branches that weren't obviously stale, analyze if the work was superseded:

1. Look at PR titles and commit messages
2. Compare with recent trunk commits
3. If similar work was merged via different branch, suggest cleanup
4. Ask user to confirm

## Output Format

After completing analysis:

```
## Summary

- Deleted N branches (list names)
- Kept N branches (list names with reason)
- Skipped N branches (user declined)

## Branches Requiring Manual Review

- `branch-name`: Reason why it needs manual review
```

## Notes

- Use `git worktree remove` before deleting branches checked out in worktrees
- Use `-D` (force) for branch deletion since branches may not be fully merged
- Never delete trunk branch (main/master)
- Never delete branches with open PRs without explicit confirmation
- Always show PR URL when available for easy reference

## Error Handling

If the kit CLI command fails:

```
Error: Could not gather branch data

Possible causes:
- Not in a git repository
- GitHub CLI (gh) not authenticated

To authenticate:
    gh auth login
```

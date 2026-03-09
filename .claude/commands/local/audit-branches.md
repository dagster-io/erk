---
description: Audit and clean up stale branches, worktrees, and PRs
---

# /audit-branches

Automates the branch audit workflow using pre-collected, categorized data.

## Agent Instructions

### Phase 1: Collect Data

Run the audit-collect command to get pre-categorized JSON:

```bash
erk-dev audit-collect
```

Parse the JSON output. The structure contains:

- `summary`: `total_local_branches`, `total_worktrees`, `total_open_prs`
- `categories.blocking_worktrees`: Worktrees with closed/merged PRs blocking cleanup
- `categories.auto_cleanup`: Branches safe to delete (0 ahead, no unique work)
- `categories.closed_pr_branches`: Branches with closed/merged PRs
- `categories.pattern_branches.async_learn`: Grouped `async-learn/*` branches
- `categories.stale_open_prs`: Open PRs that appear stale/superseded
- `categories.needs_attention`: Open PRs with conflicts or issues
- `categories.active`: Count of healthy open PRs (skipped)
- `stubs_tracked_by_graphite`: Stub branches accidentally tracked by Graphite

If `success` is false, display the error and stop.

### Phase 1b: Cross-Reference Graphite Stack

The `audit-collect` command may miss stale plan branches that are tracked by Graphite but have closed/merged PRs. These appear as "active" in audit-collect but are actually dead.

Run `gt log short --no-interactive` to get the full Graphite stack, then for any `plnd/*` branches NOT already categorized by audit-collect, check their PR state:

```bash
gh pr list --head "<branch>" --state all --json number,state --jq '.[0] | "\(.number) \(.state)"'
```

Also check commits ahead: `git rev-list --count master.."<branch>"`

Branches with closed/merged PRs (especially those with only 1 commit ahead — just the plan commit) are safe to delete. Add them to the cleanup list.

For each, untrack from Graphite before deleting:
```bash
gt branch untrack "<branch>" --no-interactive --force
git branch -D "<branch>"
git push origin --delete "<branch>" 2>/dev/null || true
```

### Phase 2: Untrack Stubs

If `stubs_tracked_by_graphite` is non-empty, untrack each stub from Graphite:

```bash
gt branch untrack "<stub-name>" --no-interactive --force
```

### Phase 3: Present Findings

Display each non-empty category as a table:

**Summary:**

```
Total: {total_local_branches} local branches, {total_worktrees} worktrees, {total_open_prs} open PRs
```

**Blocking Worktrees** (if any):

| Worktree    | Branch   | PR           | Status     | Action                                          |
| ----------- | -------- | ------------ | ---------- | ----------------------------------------------- |
| {slot_name} | {branch} | #{pr_number} | {pr_state} | {is_slot ? "Unassign slot" : "Remove worktree"} |

**Auto-Cleanup** (if any):

| Branch   | Reason   | Has Remote   |
| -------- | -------- | ------------ |
| {branch} | {reason} | {has_remote} |

For `planned-pr-context/*` branches in auto-cleanup: extract the PR number from the branch name (e.g., `planned-pr-context/8939` → PR #8939), check each PR's state via `gh pr view <number> --json state -q .state`, and separate into:
- **Closed/Merged PR**: safe to delete (include in cleanup)
- **Open PR**: keep (exclude from cleanup)

Present them as a sub-table showing which are deletable vs kept.

**Closed PR Branches** (if any):

| Branch   | PR           | Status     | In Worktree   | Graphite              |
| -------- | ------------ | ---------- | ------------- | --------------------- |
| {branch} | #{pr_number} | {pr_state} | {in_worktree} | {tracked_by_graphite} |

**Pattern Branches** (if any):

For `async_learn`: "{count} async-learn/\* branches" with parent PR state breakdown.

**Needs Attention** (if any):

| PR           | Title   | Mergeable   | Branch   |
| ------------ | ------- | ----------- | -------- |
| #{pr_number} | {title} | {mergeable} | {branch} |

**Active PRs**: "{count} active open PRs (skipped)"

### Phase 4: User Selection

Use AskUserQuestion to ask which categories to clean up:

- "Free all blocking worktrees (unassign slots / remove non-slots)"
- "Delete all auto-cleanup branches (no unique work)"
- "Delete all closed-PR branches"
- "Delete all async-learn/\* pattern branches"
- "Close stale open PRs"
- "Skip cleanup for now"

Allow user to exclude specific items by number/name.

### Phase 5: Execute Cleanup

**IMPORTANT: Free blocking worktrees FIRST**, then run `gt repo sync` before other cleanup.

Execute in this order:

**Step 1: Free blocking worktrees** (if selected):

For slot worktrees:

```bash
erk slot unassign "<slot_name>"
```

If that fails (uncommitted changes):

```bash
cd <worktree_path> && git checkout . && git clean -fd
erk slot unassign "<slot_name>"
```

For non-slot worktrees:

```bash
git worktree remove --force "<worktree_path>"
```

Then prune and sync:

```bash
git worktree prune
gt repo sync --no-interactive --force --no-restack
```

**Step 2: Close stale PRs** (if selected):

```bash
gh pr close <number> --comment "Closing as part of branch audit: <reason>"
```

**Step 3: Delete closed-PR branches** not cleaned by gt sync:

For each branch, use the Branch Deletion Decision Tree:

1. Check if in worktree: `git worktree list | grep "\[<branch>\]"`
   - If slot: `erk slot unassign <slot>`
   - If non-slot: `git worktree remove --force <path>`
2. Check if tracked by Graphite (from `tracked_by_graphite` field):
   - If yes: `gt delete "<branch>" --force --no-interactive`
   - If no: `git branch -D "<branch>"`

**Step 4: Delete pattern branches** (if selected):

```bash
git branch -D "<branch>"
git push origin --delete "<branch>" 2>/dev/null || true
```

**Step 5: Delete auto-cleanup branches** (if selected):

Same Branch Deletion Decision Tree as Step 3.

**Step 6: Final prune:**

```bash
git worktree prune
```

### Phase 6: Summary

```
## Audit Complete

**Actions Taken:**
- Freed X blocking worktrees
- Closed X stale PRs
- Deleted X branches

**Remaining:**
- X PRs need attention
- X active open PRs
```

## Error Handling

- If a branch deletion fails, continue with others and report failures at end
- If PR close fails, note it and continue
- Always run `git worktree prune` at the end regardless

## Related Commands

For assessing whether a PR has been superseded:

```bash
/local:check-superceded <pr-number>
```

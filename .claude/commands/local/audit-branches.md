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

**Shell Compatibility Note:** Complex bash pipelines may not work correctly in zsh. For multi-step scripts, write to a temporary file and execute with `bash`:

```bash
cat <<'SCRIPT' > /tmp/script.sh
#!/bin/bash
# ... complex logic ...
SCRIPT
bash /tmp/script.sh
```

### Phase 1: Data Collection

Collect comprehensive data about the repository state. Run these commands to gather information:

**Step 1: Get all PRs (open and closed):**

```bash
gh pr list --state all --limit 100 --json number,title,state,headRefName,updatedAt,mergeable,isDraft
```

**Step 2: List all worktrees:**

```bash
git worktree list
```

**Step 3: Get all local branches:**

```bash
git branch --format='%(refname:short)'
```

**Step 4: Get all remote branches:**

```bash
git branch -r --format='%(refname:short)' | grep -v HEAD
```

**Step 5: Get recent commit info for each branch (batch by 10):**
For each branch, get the last commit:

```bash
git log -1 --format="%h %s (%cr)" origin/<branch> 2>/dev/null || echo "no remote"
```

**Step 6: Identify local-only branches:**
Branches that exist locally but have no remote tracking branch.

**Step 7: Detect worktree anomalies:**

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

### Phase 3: No-PR Worktree Analysis

For worktrees without associated PRs:

**Step 1: Get unique commits:**

```bash
git log master..HEAD --oneline  # from worktree directory
```

**Step 2: Analyze actual code content:**

- **Empty** (0 unique commits) → Safe to delete
- **Has commits** → Examine the actual code changes:
  - `git diff master --stat` to see scope
  - `git log master..HEAD -p -- '*.py'` to see implementation
  - Determine: What feature/fix does this implement?
  - Check if that feature exists in master via different implementation

### Phase 4: Local-Only Branch Deep Analysis

For branches without remotes (detected in Phase 1), automatically categorize based on their relationship to master:

**Step 1: Identify local-only branches and their status:**

```bash
cat <<'SCRIPT' > /tmp/local_branch_analysis.sh
#!/bin/bash
echo "| Branch | Ahead of Master | Merged to Master | Category | Last Commit |"
echo "|--------|-----------------|------------------|----------|-------------|"

for branch in $(git branch --format='%(refname:short)' | grep -v master); do
  # Skip stub branches
  [[ "$branch" == "__erk-slot-"* ]] && continue

  # Check if has remote
  has_remote=$(git branch -r | grep -q "origin/$branch" && echo "YES" || echo "NO")
  [[ "$has_remote" == "YES" ]] && continue  # Skip branches with remotes

  # Analyze local-only branch
  ahead=$(git rev-list --count master.."$branch" 2>/dev/null || echo "0")
  merged=$(git branch --merged master | grep -qE "^\s*$branch$" && echo "YES" || echo "NO")
  last_commit=$(git log -1 --format="%s" "$branch" 2>/dev/null | head -c 40 || echo "N/A")

  # Categorize
  if [[ "$merged" == "YES" ]]; then
    category="🟠 AUTO-CLEANUP (merged)"
  elif [[ "$ahead" == "0" ]]; then
    category="🟠 AUTO-CLEANUP (stale pointer)"
  else
    category="🔵 NEEDS REVIEW ($ahead commits)"
  fi

  echo "| $branch | $ahead | $merged | $category | $last_commit... |"
done
SCRIPT
bash /tmp/local_branch_analysis.sh
```

**Step 2: Categorization:**

| Category                     | Detection                                             | Action                          |
| ---------------------------- | ----------------------------------------------------- | ------------------------------- |
| **Already merged to master** | 0 commits ahead + `merged=YES`                        | Auto-flag for deletion          |
| **Stale pointer**            | 0 commits ahead + `merged=NO` (pointer to old master) | Auto-flag for deletion          |
| **Has unique commits**       | >0 commits ahead                                      | Requires user review in Phase 5 |

The first two categories (🟠 AUTO-CLEANUP) are safe to delete without user confirmation - they contain no unique work.

### Phase 5: Deep Content Analysis (for uncertain branches)

For branches that aren't clearly stale or clearly valuable:

1. **View actual code changes**: `git log master..HEAD -p -- '*.py'`
2. **Identify the thesis**: What feature/improvement was this trying to implement?
3. **Check if feature exists in master**: Search for key function/class names
4. **Assess value**: Is the idea worth reimplementing even if code is stale?

### Phase 6: Blocking Worktree Detection

**CRITICAL**: Branches with closed/merged PRs that are checked out in worktrees block automated cleanup via `gt repo sync`. Detect these first.

**Step 1: Fetch all closed/merged PRs:**

```bash
gh pr list --state closed --limit 300 --json number,headRefName,state,mergedAt \
  | jq -r '.[] | "\(.headRefName)|\(.number)|\(if .mergedAt then "MERGED" else "CLOSED" end)"' \
  > /tmp/closed_prs.txt
```

**Step 2: Get branches in worktrees:**

```bash
git worktree list --porcelain | grep "^branch refs/heads/" | sed 's|branch refs/heads/||' > /tmp/wt_branches.txt
```

**Step 3: Cross-reference to find blocking worktrees:**

Create a bash script to handle this reliably (avoids zsh pipe issues):

```bash
cat <<'SCRIPT' > /tmp/find_blocking.sh
#!/bin/bash
echo "=== SLOT WORKTREES blocking cleanup ==="
git worktree list | grep "erk-slot-" | while read line; do
  path=$(echo "$line" | awk '{print $1}')
  branch=$(echo "$line" | grep -oE '\[[^]]+\]' | tr -d '[]')

  # Skip stub branches
  if [[ "$branch" == "__erk-slot-"* ]]; then
    continue
  fi

  pr_info=$(grep "^${branch}|" /tmp/closed_prs.txt 2>/dev/null | head -1)
  if [ -n "$pr_info" ]; then
    slot=$(basename "$path")
    pr_num=$(echo "$pr_info" | cut -d'|' -f2)
    pr_status=$(echo "$pr_info" | cut -d'|' -f3)
    echo "$slot | $branch | PR#$pr_num | $pr_status"
  fi
done

echo ""
echo "=== NON-SLOT WORKTREES blocking cleanup ==="
git worktree list | grep -v "erk-slot" | grep -v "/code/erk " | while read line; do
  path=$(echo "$line" | awk '{print $1}')
  branch=$(echo "$line" | grep -oE '\[[^]]+\]' | tr -d '[]')

  pr_info=$(grep "^${branch}|" /tmp/closed_prs.txt 2>/dev/null | head -1)
  if [ -n "$pr_info" ]; then
    pr_num=$(echo "$pr_info" | cut -d'|' -f2)
    pr_status=$(echo "$pr_info" | cut -d'|' -f3)
    echo "$(basename $path) | $branch | PR#$pr_num | $pr_status"
  fi
done
SCRIPT
bash /tmp/find_blocking.sh
```

### Phase 7: Categorization

Present branches/PRs in these categories:

**🟠 AUTO-CLEANUP** - Branches safe to delete without user decision

- Local-only branches that are 0 commits ahead of master
- Local-only branches already merged to master
- These contain no unique work and can be deleted automatically

**🔴 SHOULD CLOSE** - PRs that should be closed

- Include context-based reason for each (superseded, duplicate, abandoned, etc.)
- NOT just "old" - must have a specific reason

**🟣 BLOCKING WORKTREES** - Worktrees preventing cleanup

- Branches with closed/merged PRs that are checked out in worktrees
- These block `gt repo sync` from cleaning up automatically
- **Slot worktrees**: Need `erk slot unassign` to free
- **Non-slot worktrees**: Need `git worktree remove --force` to free

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

### Phase 8: Present Findings

Present the analysis in tables for each category:

```markdown
## 🟠 AUTO-CLEANUP (X branches)

These branches contain NO unique work and can be safely deleted:

| Branch       | Category       | Reason                      |
| ------------ | -------------- | --------------------------- |
| old-local    | Stale pointer  | 0 commits ahead, not merged |
| merged-local | Already merged | 0 commits ahead, merged=YES |

## 🔴 SHOULD CLOSE (X PRs)

| PR   | Title     | Reason             | Last Updated |
| ---- | --------- | ------------------ | ------------ |
| #123 | Feature X | Superseded by #456 | 3 weeks ago  |

## 🟣 BLOCKING WORKTREES (X worktrees)

| Worktree    | Branch        | PR    | Status | Action          |
| ----------- | ------------- | ----- | ------ | --------------- |
| erk-slot-03 | P1234-feat... | #1234 | CLOSED | Unassign slot   |
| my-worktree | P5678-fix...  | #5678 | MERGED | Remove worktree |

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

### Phase 9: User Interaction

After presenting findings, ask the user what they want to do:

**Use AskUserQuestion tool to get user selection:**

Ask which categories to act on:

- "Delete all 🟠 AUTO-CLEANUP branches (no unique work)"
- "Free all 🟣 BLOCKING WORKTREES (unassign slots / remove non-slots)"
- "Close all 🔴 SHOULD CLOSE PRs"
- "Delete all 🟡 CLEANUP branches"
- "Review 🟢 CONSIDER MERGING individually"
- "Skip cleanup for now"

**Important**: Free blocking worktrees FIRST, then run `gt repo sync` to let Graphite automatically clean up the freed branches before doing other cleanup.

Allow user to exclude specific branches/PRs by number if needed.

### Phase 10: Execution

**IMPORTANT: Confirm before each destructive operation type.**

**Pre-Check: Build Worktree Map**

Before deleting ANY branches, build a map of which branches are in worktrees:

```bash
cat <<'SCRIPT' > /tmp/build_worktree_map.sh
#!/bin/bash
# Build map of branch -> worktree path
declare -A branch_worktrees
while read line; do
  path=$(echo "$line" | awk '{print $1}')
  branch=$(echo "$line" | grep -oE '\[[^]]+\]' | tr -d '[]')
  if [[ -n "$branch" ]]; then
    echo "$branch|$path"
  fi
done < <(git worktree list)
SCRIPT
bash /tmp/build_worktree_map.sh > /tmp/branch_worktree_map.txt
```

Then for each branch to delete, check the map first:

```bash
worktree_path=$(grep "^$branch|" /tmp/branch_worktree_map.txt | cut -d'|' -f2)
if [ -n "$worktree_path" ]; then
  echo "Branch $branch is in worktree at $worktree_path - must free first"
fi
```

Execute in this order:

**Step 0: Delete AUTO-CLEANUP branches (if selected):**

These branches have no unique work (0 commits ahead of master or already merged). Apply the Branch Deletion Decision Tree for each:

```bash
for branch in <auto-cleanup-branches>; do
  # Check worktree map first
  worktree_path=$(grep "^$branch|" /tmp/branch_worktree_map.txt | cut -d'|' -f2)
  if [ -n "$worktree_path" ]; then
    # Free worktree first (see decision tree)
    if [[ "$worktree_path" =~ erk-slot-[0-9]{2} ]]; then
      slot=$(basename "$worktree_path")
      erk slot unassign "$slot" || {
        (cd "$worktree_path" && git checkout . && git clean -fd)
        erk slot unassign "$slot"
      }
    else
      git worktree remove --force "$worktree_path"
    fi
  fi

  # Now delete the branch
  if gt log short 2>/dev/null | grep -q "$branch"; then
    gt delete "$branch" --force --no-interactive
  else
    git branch -D "$branch"
  fi
done
```

**Step 1: Free blocking worktrees (if selected):**

This must happen FIRST to unblock automated cleanup.

Unassign slot worktrees (with uncommitted changes handling):

```bash
free_slot_worktree() {
  local slot=$1
  local path=$(git worktree list | grep "$slot" | awk '{print $1}')

  if ! erk slot unassign "$slot" 2>/dev/null; then
    echo "Slot $slot has uncommitted changes, discarding..."
    (cd "$path" && git checkout . && git clean -fd)
    erk slot unassign "$slot"
  fi
}

for slot in <slot-list>; do
  free_slot_worktree "$slot"
done
```

Remove non-slot worktrees:

```bash
for path in <non-slot-paths>; do
  git worktree remove --force "$path"
done
```

Prune and sync:

```bash
git worktree prune
gt repo sync --no-interactive --force --no-restack
```

This lets Graphite automatically clean up the now-freed branches with closed/merged PRs.

**Step 2: Close PRs (if selected):**

```bash
gh pr close <number> --comment "Closing as part of branch audit: <reason>"
```

**Step 3: Remove worktrees (if applicable):**

```bash
git worktree remove --force <path>
```

**Step 4: Run gt repo sync for automated cleanup:**

After freeing blocking worktrees, `gt repo sync` handles most branch deletion automatically:

```bash
gt repo sync --no-interactive --force --no-restack
```

This automatically:

- Deletes local branches with closed/merged PRs
- Cleans up remote tracking branches

**Step 5: Manual cleanup for non-Graphite branches:**

For branches not tracked by Graphite (won't be cleaned by `gt sync`):

Check if branch is in a worktree:

```bash
worktree_path=$(git worktree list | grep "\[$branch\]" | awk '{print $1}')
```

If in a worktree, free it first:

```bash
if [ -n "$worktree_path" ]; then
  if [[ "$worktree_path" =~ erk-slot-[0-9]{2} ]]; then
    erk slot unassign "$worktree_path"
  else
    git worktree remove --force "$worktree_path"
  fi
fi
```

Delete local and remote branches:

```bash
git branch -D "$branch"
git push origin --delete "$branch" 2>/dev/null || true
```

**Step 6: Final prune:**

```bash
git worktree prune
```

### Phase 11: Summary

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

## Branch Deletion Decision Tree

**CRITICAL**: Before deleting ANY branch, follow this exact sequence:

```
1. Is branch in a worktree?
   └─ Check: git worktree list | grep "\[$branch\]"

   YES → Free the worktree FIRST:
   │  ├─ Is it a slot worktree (erk-slot-NN)?
   │  │   └─ YES:
   │  │       1. Try: erk slot unassign <slot>
   │  │       2. If fails (uncommitted changes):
   │  │          cd <worktree-path> && git checkout . && git clean -fd
   │  │       3. Retry: erk slot unassign <slot>
   │  │
   │  └─ NO (vanilla worktree):
   │       └─ git worktree remove --force <path>
   │
   NO → Proceed to step 2

2. Is branch tracked by Graphite?
   └─ Check: gt log short 2>/dev/null | grep -q "$branch"

   YES → gt delete "$branch" --force --no-interactive
   NO  → git branch -D "$branch"
```

**Why this order matters:**

- Deleting a branch while it's checked out in a worktree will fail
- `erk slot unassign` preserves the slot directory for reuse; `git worktree remove` deletes it
- Graphite-tracked branches need `gt delete` to properly clean up metadata and re-parent stacks
- Non-Graphite branches (local experiments, old migrations) use standard `git branch -D`

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

## Related Commands

For assessing a single PR or plan's relevance (faster than a full audit), use:

```bash
/local:check-relevance <issue-number>
```

This provides focused, inline assessment during development workflows when you need to quickly determine if specific work is already implemented.

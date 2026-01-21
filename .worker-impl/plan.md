# Improve audit-branches: Worktree Blocking Detection

## Problem Summary

The audit-branches session revealed a critical gap: branches with closed/merged PRs that are checked out in worktrees **block** `gt repo sync` from cleaning them up. The current documentation doesn't explicitly detect or handle this case.

## Key Learnings from Session

1. **Blocking worktrees must be detected first**: Before any cleanup, identify branches where:
   - Branch has a closed/merged PR
   - Branch is currently checked out in a worktree
   - This blocks automated cleanup

2. **Categorize by worktree type**:
   - **Slot worktrees** (`erk-slot-NN`): Use `erk slot unassign <slot>` to free
   - **Non-slot worktrees**: Use `git worktree remove --force <path>` to remove entirely

3. **Leverage gt repo sync**: After freeing branches, `gt repo sync --no-interactive --force` handles:
   - Deleting branches with closed/merged PRs
   - Cleaning up remote tracking
   - Restacking remaining branches

4. **Bash vs zsh**: Session had pipe issues in zsh. Scripts should use explicit `bash` for complex logic.

## Proposed Changes

### File: `.claude/commands/local/audit-branches.md`

### 1. Add New Phase 2.8: Blocking Worktree Detection

Insert after Phase 2.7, before Phase 3:

```markdown
### Phase 2.8: Blocking Worktree Detection

**CRITICAL**: Branches with closed/merged PRs that are checked out in worktrees block automated cleanup.

**2.8.1 Fetch all closed/merged PRs:**
```bash
gh pr list --state closed --limit 300 --json number,headRefName,state,mergedAt \
  | jq -r '.[] | "\(.headRefName)|\(.number)|\(if .mergedAt then "MERGED" else "CLOSED" end)"' \
  > /tmp/closed_prs.txt
```

**2.8.2 Get branches in worktrees:**
```bash
git worktree list --porcelain | grep "^branch refs/heads/" | sed 's|branch refs/heads/||' > /tmp/wt_branches.txt
```

**2.8.3 Cross-reference to find blocking worktrees:**

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
```

### 2. Add New Category to Phase 3

Add between 🔴 SHOULD CLOSE and 🟡 CLEANUP:

```markdown
**🟣 BLOCKING WORKTREES** - Worktrees preventing cleanup

These branches have closed/merged PRs but are checked out in worktrees, blocking automated cleanup:

| Worktree | Branch | PR | Status | Action |
|----------|--------|-----|--------|--------|
| erk-slot-03 | P1234-... | #1234 | CLOSED | Unassign slot |
| my-worktree | P5678-... | #5678 | MERGED | Remove worktree |
```

### 3. Update Phase 5 (User Interaction)

Add option:
- "Free all 🟣 BLOCKING WORKTREES (unassign slots / remove non-slots)"

### 4. Add New Phase 6.0: Free Blocking Worktrees

Insert before existing 6.1:

```markdown
**6.0 Free blocking worktrees (if selected):**

**6.0.1 Unassign slot worktrees:**
```bash
for slot in <slot-list>; do
  erk slot unassign "$slot"
done
```

**6.0.2 Remove non-slot worktrees:**
```bash
for path in <non-slot-paths>; do
  git worktree remove --force "$path"
done
```

**6.0.3 Prune and sync:**
```bash
git worktree prune
gt repo sync --no-interactive --force
```

This lets Graphite automatically clean up the now-freed branches.
```

### 5. Update Phase 6.3-6.4

Simplify since gt repo sync handles most cleanup:

```markdown
**6.3 Run gt repo sync for remaining cleanup:**

After freeing blocking worktrees, `gt repo sync` handles most branch deletion:
```bash
gt repo sync --no-interactive --force
```

This automatically:
- Deletes local branches with closed/merged PRs
- Cleans up remote tracking branches
- Restacks remaining branches on master

**6.4 Manual cleanup for non-Graphite branches:**

For branches not tracked by Graphite (won't be cleaned by gt sync):
```bash
git branch -D <branch>
git push origin --delete <branch>
```
```

### 6. Add Shell Compatibility Note

Add to top of Agent Instructions:

```markdown
**Shell Compatibility Note:** Complex bash pipelines may not work correctly in zsh. For multi-step scripts, write to a temporary file and execute with `bash`:
```bash
cat <<'SCRIPT' > /tmp/script.sh
#!/bin/bash
# ... complex logic ...
SCRIPT
bash /tmp/script.sh
```
```

## Verification

1. Run `/audit-branches` on a repo with:
   - Slots assigned to branches with closed PRs
   - Non-slot worktrees with closed PRs
2. Verify the 🟣 BLOCKING WORKTREES category appears
3. Select "Free blocking worktrees" option
4. Verify slots are unassigned and non-slots removed
5. Verify `gt repo sync` cleans up the freed branches
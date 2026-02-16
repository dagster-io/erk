---
title: Graphite Stack Troubleshooting
read_when:
  - "debugging Graphite stack operation failures"
  - "recovering from gt sync or gt submit errors"
  - "fixing stack ordering or parent tracking issues"
tripwires:
  - action: "running gt sync without verifying clean working tree"
    warning: "gt sync performs a rebase that can lose uncommitted changes. Commit or stash first. See docs/learned/workflows/git-sync-state-preservation.md"
  - action: "running git rebase, git cherry-pick, or git reset"
    warning: "Always run `gt track --no-interactive` immediately after raw git operations that change commit SHAs. Without this, `gt restack` will fail with 'diverged from tracking' errors because Graphite's cache (.graphite_cache_persist) still references old SHAs."
---

# Graphite Stack Troubleshooting

Common failures and recovery patterns for Graphite stack operations.

## Common Failures

### gt sync Fails with Conflicts

**Symptom**: `gt sync` reports merge conflicts during rebase.

**Recovery**:

1. Resolve conflicts in the affected files
2. `git add <resolved-files>`
3. `gt continue` to resume the rebase
4. If unrecoverable: `gt abort` to cancel and return to pre-sync state

### gt submit Fails with Stale Stack

**Symptom**: `gt submit` fails because the stack is out of date.

**Recovery**:

1. `gt sync` to update the stack
2. Resolve any conflicts
3. Retry `gt submit`

### Branch Has Wrong Parent

**Symptom**: A branch appears under the wrong parent in the Graphite stack.

**Recovery**:

1. `gt track --parent <correct-parent>` to fix the parent
2. `gt sync` to rebase onto the correct parent

### Stack Shows Deleted Branches

**Symptom**: `gt log` shows branches that were already deleted.

**Recovery**:

1. `gt sync` to refresh stack state from remote
2. If branches persist: `gt untrack <branch>` to remove them

### Graphite Cache Staleness After Raw Git Operations

**Symptom**: After running `git rebase`, `gt restack` fails with "diverged from tracking" error.

**Root cause**: Raw git operations that rewrite history (rebase, cherry-pick, reset) change commit SHAs but Graphite's internal cache (`.graphite_cache_persist`) still references old SHAs.

**Recovery**:

```bash
git rebase origin/branch-name  # Changes commit SHAs
gt track --no-interactive      # MUST run to update Graphite cache
gt restack --no-interactive    # Now safe to restack
```

This pattern was discovered during sync-divergence resolution. See the `sync-divergence` skill for the complete workflow.

## Prevention

- Always commit or stash before `gt sync` (see [Git Sync State Preservation](../workflows/git-sync-state-preservation.md))
- Run `gt log` after operations to verify stack state
- Use `gt stack` to verify the current stack before submitting

## Related Documentation

- [Git Sync State Preservation](../workflows/git-sync-state-preservation.md) — Protecting working tree during sync

# Fix: Prevent gt repo sync from restacking active branches

## Problem

`gt repo sync --no-interactive --force` restacks ALL Graphite-tracked branches onto current master by default. This contaminates active branches with master commits, causing Graphite tracking divergence.

## Root Cause

`gt repo sync` has `--restack` defaulting to TRUE. When run during audit-branches, it restacks branches that may be actively worked on in other sessions, polluting their history.

## Solution

Add `--no-restack` flag to all `gt repo sync` commands in audit-branches.md.

### File: `.claude/commands/local/audit-branches.md`

**Change 1: Line 334 (Phase 6.0.3)**
```bash
# Before:
gt repo sync --no-interactive --force

# After:
gt repo sync --no-interactive --force --no-restack
```

**Change 2: Line 356 (Phase 6.3)**
```bash
# Before:
gt repo sync --no-interactive --force

# After:
gt repo sync --no-interactive --force --no-restack
```

**Change 3: Update Phase 6.3 description (lines 359-363)**

Update the "This automatically:" section to remove the restacking bullet since we're disabling it:
- Remove: "Restacks remaining branches on master"

## Verification

1. Run `/audit-branches` on a repo with active branches
2. Verify `gt repo sync --no-restack` is used
3. Confirm active branches are NOT restacked onto master
---
title: Stack Sync Command
read_when:
  - "working with erk stack sync"
  - "resolving branch divergence across stack"
  - "syncing stack branches with remote"
tripwires: []
---

# Stack Sync Command

## Overview

`erk stack sync` is a hidden command that syncs all branches in the current Graphite stack with their remote tracking branches.

## Usage

```bash
erk stack sync
```

## Behavior

- Fetches remote state for all branches in the stack
- Resolves divergences via fast-forward or rebase
- Automatic restack after syncing
- Detects conflicts and suggests `erk pr diverge-fix`
- Skips branches checked out in other worktrees

## Output Format

Per-branch results with action label and detail:

```
  feature-a              already in sync
  feature-b              fast-forwarded (3 commits)
  feature-c              CONFLICT — run: erk pr diverge-fix

Restacking... done

Stack synced: 1 fixed, 1 in sync, 1 conflict
```

Summary statistics: fixed/in-sync/conflicts/skipped.

## Implementation

- CLI: `src/erk/cli/commands/stack/sync_cmd.py`
- Core logic: `src/erk/core/stack_sync.py`
- Hidden command (not shown in `erk --help`)
- Uses `GraphiteCommand` class

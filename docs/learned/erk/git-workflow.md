---
title: Git Workflow with Graphite
read_when:
  - "pushing branches managed by Graphite"
  - "resolving divergence after rebase on Graphite-managed branches"
  - "deciding between git push and gt submit"
last_audited: "2026-02-15 17:17 PT"
---

# Git Workflow with Graphite

## Graphite-Managed Branches

For branches managed by Graphite, use `gt submit --no-interactive` instead of `git push`.

### Why

- Graphite tracks branch relationships for stacking
- Direct `git push` bypasses Graphite's metadata updates
- After rebase or amend, `git push` will be rejected with non-fast-forward error because local history diverges from remote

### After Rebase

If local history diverges from remote after rebase:

1. Use `/erk:sync-divergence` command (preferred)
2. Or manually: `gt track` → `gt restack` → `gt submit --no-interactive`

### Common Pitfall

Direct `git push` after removing a WIP commit via rebase will fail because the remote still has the old commit history. This is expected behavior — use `gt submit` which handles force-push correctly within Graphite's tracking system.

## Related

- [Git and Graphite Edge Cases](../architecture/git-graphite-quirks.md) — Detailed edge case catalog

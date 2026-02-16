---
title: Rebase Conflict Resolution Strategy
description: When to use git checkout --ours vs manual resolution in rebases
read_when:
  - resolving rebase conflicts
  - branch conflicts with merged PR
  - choosing between conflicting implementations
tripwires:
  - action: "resolving rebase conflicts with a merged PR"
    warning: "Prefer HEAD's reviewed implementation (git checkout --ours). The merged code has passed review."
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
---

# Rebase Conflict Resolution Strategy

## Merged PR Precedence

When rebasing and conflicts occur with an already-merged PR:

**Take HEAD (`git checkout --ours`)** - the merged code has passed review.

## Heuristics

### Take HEAD when:

- Base contains merged, reviewed implementation
- HEAD uses erk conventions (LBYL over EAFP)
- HEAD preserves format, branch forces conversion

### Manual resolution when:

- Both implementations have unique value
- Downstream commits depend on branch's approach
- Semantic differences require careful merging

## Auto-Drop Detection

Git detects "already upstream" commits and auto-drops them during rebase. This is expected when rebasing after dependent PR merges.

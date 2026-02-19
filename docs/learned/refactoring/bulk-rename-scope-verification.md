---
title: Bulk Rename Scope Verification
read_when:
  - "running bulk rename tools (sed, libcst, ast-grep)"
  - "verifying scope after a batch rename"
  - "distinguishing TUI renames from API renames"
tripwires:
  - action: "completing a bulk rename without checking git diff --stat"
    warning: "Use git diff --stat to verify only expected files changed. Spot-check for semantic boundary violations (e.g., TUI data types vs GitHub API types sharing the same field name)."
  - action: "running a bulk rename that touches both TUI and API layer files"
    warning: "Bulk rename tools operate syntactically, not semantically. A term like issue_number may appear in both TUI data structures (PlanRowData) and GitHub API structures (Issue.json) - these are different semantic domains that should not be renamed together."
---

# Bulk Rename Scope Verification

After running bulk rename tools, verify that only the intended files were changed.

## Why This Matters

Bulk rename tools operate syntactically, not semantically. A term like `issue_number` may appear in both TUI data structures (`PlanRowData`) and GitHub API structures (`Issue.json`) — these are different semantic domains that should not be renamed together.

## Verification Steps

1. Run `git diff --stat` after the bulk rename
2. Check if unexpected files appear in the list
3. For files outside intended scope, revert with `git checkout HEAD -- <path>`
4. Spot-check 2-3 modified files to verify semantic correctness

## Example

After renaming `issue_number` -> `plan_id` in the TUI layer:

```bash
git diff --stat
# Expected: src/erk/tui/*, packages/erk-shared/src/erk_shared/gateway/plan_data_provider/*
# Unexpected: src/erk/gateway/github/* (GitHub API layer - should NOT be renamed)
```

If unexpected files appear:

```bash
git checkout HEAD -- src/erk/gateway/github/
```

## Related Documentation

- [Systematic Terminology Renames](systematic-terminology-renames.md) — three-phase rename workflow
- [Scope Discipline in Renames](scope-discipline.md) — TUI vs API layer boundaries

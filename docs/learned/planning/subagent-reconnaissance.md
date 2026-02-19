---
title: Subagent Reconnaissance Before Bulk Refactors
read_when:
  - "planning bulk rename operations"
  - "launching libcst-refactor for large changes"
  - "scoping refactoring tasks"
tripwires:
  - action: "launching a bulk rename without first counting occurrences"
    warning: "Launch Explore subagents to understand scope before executing. Upfront reconnaissance prevents under-renaming (missing files) and over-renaming (changing wrong semantic domains)."
---

# Subagent Reconnaissance Pattern

Before executing bulk renames, launch Explore subagents to understand scope.

## Why This Matters

The PR #7473 implementation discovered 176 occurrences across 19 files. This upfront reconnaissance:

- Prevents under-renaming (missing files)
- Prevents over-renaming (changing wrong semantic domains)
- Enables accurate scope estimation

## Reconnaissance Queries

Launch Explore subagents to:

1. **Find method signatures:** "Find all method signatures with parameter named `issue_number`"
2. **Count field access:** "Count occurrences of `.issue_number` field access across packages"
3. **Identify semantic boundaries:** "Which files use `issue_number` to refer to GitHub issues vs. plan identifiers?"

## Pattern

1. Launch Explore subagent for scope discovery
2. Wait for results before committing to strategy
3. Use findings to inform libcst-refactor instructions
4. After bulk rename, verify against original count

## Related Documentation

- [Bulk Rename Scope Verification](../refactoring/bulk-rename-scope-verification.md) — post-rename verification
- [Scope Discipline in Renames](../refactoring/scope-discipline.md) — TUI vs API layer boundaries

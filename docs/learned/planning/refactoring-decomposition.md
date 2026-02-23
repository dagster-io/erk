---
title: Refactoring Decomposition for Backend Elimination
read_when:
  - "deleting a function or type that has many callers across the codebase"
  - "planning a multi-node objective that removes a backend or feature flag"
  - "decomposing a large refactor into reviewable PRs"
---

# Refactoring Decomposition for Backend Elimination

When deleting a backend selector function (or feature flag reader) that has many callers spread across the codebase, decompose the work into sequential nodes.

## The Three-Node Pattern

1. **Node N: Delete definition + mechanical replacement** -- Delete the selector function and its type alias. Replace every callsite with the hardcoded return value (e.g., `"draft_pr"`). This produces tautological comparisons (`"draft_pr" == "draft_pr"`) and always-false branches (`"draft_pr" != "draft_pr"`) that are intentionally preserved. Mark dead branches with a comment tag (e.g., `PLAN_BACKEND_SPLIT`) for the next node to find.

2. **Node N+1: Remove dead branches** -- Grep for the comment tag and remove all always-true/always-false conditional blocks. This is logic simplification, not mechanical replacement.

3. **Node N+2: Remove parameters** -- Delete function parameters, class fields, and CLI options that carried the backend type through the call chain. These are now redundant since only one value is possible.

## Why This Split Matters

- Each PR is reviewable: node N is purely mechanical (no behavioral change), node N+1 is logic simplification, node N+2 is signature cleanup
- Scope creep is prevented: the temptation to "also clean up this dead branch while I'm here" is deferred to the correct node
- Rollback is granular: each node can be reverted independently

## Reference Implementation

Objective #7911 nodes 1.1-1.3 used this pattern to eliminate the `get_plan_backend()` / `PlanBackendType` dual-backend system. Node 1.1 (PR #7971) deleted definitions and replaced 24 files. Node 1.2 removes dead branches. Node 1.3 removes `plan_backend` parameters from TUI.

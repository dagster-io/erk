---
title: Metadata Update Patterns
read_when:
  - "writing plan dispatch metadata updates"
  - "choosing between assertive and best-effort metadata operations"
  - "working with write_dispatch_metadata or maybe_update_pr_dispatch_metadata"
tripwires:
  - action: "using assertive metadata writes in a best-effort context"
    warning: "write_dispatch_metadata() raises on error. maybe_update_pr_dispatch_metadata() uses LBYL guards and returns silently when preconditions aren't met (no warning printed on skip). Choose based on whether failure should block the operation."
---

# Metadata Update Patterns

Two contrasting patterns for plan dispatch metadata updates exist in `src/erk/cli/commands/pr/metadata_helpers.py`.

## Assertive: `write_dispatch_metadata()`

<!-- Source: src/erk/cli/commands/pr/metadata_helpers.py, write_dispatch_metadata -->

Raises `RuntimeError` on any failure. Used when dispatch metadata is a hard requirement.

- Calls `get_workflow_run_node_id()` — raises if None
- Calls `get_managed_pr()` — raises if PrNotFound
- Calls `update_metadata()` directly

**Use when:** The caller cannot proceed without metadata being written.

## Best-Effort: `maybe_update_pr_dispatch_metadata()`

<!-- Source: src/erk/cli/commands/pr/metadata_helpers.py, maybe_update_pr_dispatch_metadata -->

Uses LBYL guards and returns silently when preconditions aren't met. Prints a success message when metadata is successfully written.

- Checks `resolve_pr_number_for_branch()` — returns if None
- Checks `get_workflow_run_node_id()` — returns if None
- Calls `ensure_plan_header()` then `update_metadata()` if both checks pass
- Prints a success message on completion (no warning on skip — it simply returns)

**Use when:** Metadata update is optional and should not block the primary operation.

## Key Insight: Two-Guard LBYL Pattern

`maybe_update_pr_dispatch_metadata()` demonstrates proper LBYL for best-effort operations. It uses two sequential guards (branch resolves to a PR, workflow run has a node ID) and returns early if either is missing. There is no set-based field validation — `ensure_plan_header()` handles initialization before `update_metadata()` writes the fields.

---
title: Learn Command Conditional Pipeline
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
read_when:
  - "modifying the erk learn command flow"
  - "adding session discovery logic to learn workflow"
  - "understanding how preprocessed materials bypass session discovery"
tripwires:
  - action: "adding session discovery code before checking for preprocessed materials"
    warning: "Check learn branch first to avoid misleading output. The learn command checks _get_learn_materials_branch() BEFORE session discovery. If a learn branch exists, all session discovery is skipped."
---

# Learn Command Conditional Pipeline

The `erk learn` command checks for preprocessed materials **before** session discovery, avoiding expensive and misleading session lookup when materials already exist.

## Pattern: Check Preprocessed Before Discovery

<!-- Source: src/erk/cli/commands/learn/learn_cmd.py, learn_cmd -->

The `learn_cmd()` function in `src/erk/cli/commands/learn/learn_cmd.py` checks for a learn materials branch before session discovery:

1. `_get_learn_materials_branch()` → checks plan header for `learn_materials_branch`
2. If branch exists:
   - Display "Preprocessed learn materials for plan" message with branch name
   - Skip ALL session discovery
   - Launch `/erk:learn` directly via `prompt_executor.execute_interactive()`
3. If no branch:
   - Existing flow: discover sessions, display, confirm, launch

## Why This Order Matters

Without the early branch check, the command would:

1. Run session discovery (which may find zero readable sessions)
2. Display confusing "no sessions found" output
3. Then somehow still need to use the preprocessed materials

The early `_get_learn_materials_branch()` call short-circuits the entire discovery pipeline, providing a cleaner user experience.

## Implementation Details

### \_get_learn_materials_branch()

<!-- Source: src/erk/cli/commands/learn/learn_cmd.py, _get_learn_materials_branch -->

See `_get_learn_materials_branch()` in `src/erk/cli/commands/learn/learn_cmd.py:237-257`. Checks the plan's metadata for a `learn_materials_branch` field via `ctx.plan_backend.get_metadata_field()`. Returns `str | None`.

Uses LBYL pattern: checks `isinstance(result, PlanNotFound)` and `isinstance(result, str)` before returning the branch name.

## Related Documentation

- [Learn Pipeline Workflow](../planning/learn-pipeline-workflow.md) — Full pipeline architecture
- [Planned PR Context Local Preprocessing](../planning/planned-pr-context-local-preprocessing.md) — How preprocessing stores sessions in the planned-pr-context branch

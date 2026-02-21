---
title: Plan Migration to Draft PR
read_when:
  - "migrating an issue-based plan to a draft PR"
  - "understanding two-phase metadata preservation during migration"
  - "debugging metadata loss after plan migration"
tripwires:
  - action: "migrating a plan without preserving operational metadata"
    warning: "create_plan() only sets a subset of fields. Use update_metadata() in a second phase to carry over operational fields like lifecycle_stage, last_dispatched_at, etc. See _FIELDS_HANDLED_BY_CREATE in plan_migrate_to_draft_pr.py."
    score: 6
---

# Plan Migration to Draft PR

The `erk exec plan-migrate-to-draft-pr` command migrates an issue-based plan to a draft-PR-backed plan. The migration uses a two-phase metadata preservation pattern.

## Two-Phase Metadata Preservation

**Location:** `src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py`

<!-- Source: src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py, plan_migrate_to_draft_pr -->

### Phase 1: `create_plan()`

Creates the draft PR with core fields: title, content, labels, and plan-header metadata. Returns a `PlanRef` with the new PR number.

### Phase 2: `update_metadata()`

Carries over operational metadata from the source issue that `create_plan()` does not handle. The `_FIELDS_HANDLED_BY_CREATE` set tracks which fields are already set by Phase 1:

<!-- Source: src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py, _FIELDS_HANDLED_BY_CREATE -->

The set includes: `schema_version`, `created_at`, `created_by`, `branch_name`, `plan_comment_id`, `source_repo`, `objective_issue`, `created_from_session`, and `created_from_workflow_run_url`.

Any fields in the source plan's header that are NOT in this set and have non-None values are carried over via `update_metadata()`. This preserves operational state like `lifecycle_stage`, `last_dispatched_at`, and future fields added to the plan-header schema.

## Post-Migration Cleanup

After creating the draft PR and preserving metadata:

1. A migration comment is added to the original issue
2. The original issue is closed

## Why Two Phases?

`create_plan()` sets certain fields through its own logic (e.g., `created_at` from the current time, `schema_version` from the constant). Passing these through `metadata` would conflict. The two-phase approach lets `create_plan()` handle its fields, then `update_metadata()` fills in the rest without overwriting.

## Related Documentation

- [Draft PR Plan Backend](draft-pr-plan-backend.md) — Backend architecture
- [Plan Backend Migration Guide](plan-backend-migration.md) — PlanBackend ABC methods

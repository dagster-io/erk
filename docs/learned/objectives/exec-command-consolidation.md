---
title: Objective Exec Command Consolidation
read_when:
  - "working with the objective-apply-landed-update exec script"
  - "modifying how objectives are updated after landing a PR"
  - "adding new discovery patterns to exec scripts"
tripwires:
  - action: "adding a required parameter to objective-apply-landed-update without fallback discovery"
    warning: "The script auto-fills missing parameters from git/plan state. New parameters should follow the same pattern: explicit flag first, then auto-discovery fallback."
  - action: "passing None for optional discovery flags and assuming defaults"
    warning: "Optional discovery flags (--plan, --objective, --pr) have complex fallback chains. Test edge cases where the fallback source is unavailable (branch deleted, plan not found, PR not created)."
    score: 5
  - action: "adding a new exec command without registering in the exec group"
    warning: "New exec scripts must be registered in the Click exec command group and follow the existing pattern: Click command with typed options, LBYL validation, structured result TypedDict."
    score: 4
---

# Objective Exec Command Consolidation

The `objective-apply-landed-update` exec script consolidates what was previously a multi-step workflow into a single command.

## Location

<!-- Source: src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py -->

`src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`

## Three-Step Consolidation

The script combines three operations into a single invocation:

1. **Fetch context** — Builds roadmap context and fetches objective content from GitHub
2. **Update nodes** — Marks relevant roadmap nodes as done with PR references, updates the comment tracking table
3. **Post action comment** — Formats and posts a structured action comment to the objective issue

## TypedDict Schema

<!-- Source: packages/erk-shared/src/erk_shared/objective_apply_landed_update_result.py -->

Result types are defined in `erk_shared/objective_apply_landed_update_result.py`:

- **`NodeUpdateDict`** — Tracks `node_id`, `previous_pr` for each updated node
- **`ApplyLandedUpdateResultDict`** — Success result including `objective`, `plan`, `pr`, `roadmap`, `node_updates`, `action_comment_id`
- **`ApplyLandedUpdateErrorDict`** — Error case with `success` flag and `error` message

## Auto-Discovery Pattern

The script auto-fills missing parameters using a cascading discovery chain:

1. **Branch** — Auto-filled from current git branch if not provided
2. **Plan** — If `--plan` is provided, use it directly (direct lookup). Otherwise, discover via `plan_backend.get_plan_for_branch()`
3. **Objective** — If `--objective` is provided, use it directly. Otherwise, extract from `plan_result.objective_id`
4. **PR** — If `--pr` is provided, use it directly. Otherwise, discover via `github.get_pr_for_branch()`

This pattern ensures the command works both when called with full context (from the land pipeline, which captures metadata before branch deletion) and when called manually with minimal arguments.

## Related Documentation

- [Objective Update After Land](../planning/objective-update-after-land.md) — Fail-open design and activation context

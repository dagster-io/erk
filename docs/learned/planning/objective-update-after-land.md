---
title: Objective Update After Land
read_when:
  - "modifying the land pipeline's post-merge behavior"
  - "working with objective-update-after-land exec script"
  - "understanding fail-open patterns in erk"
tripwires:
  - action: "making objective-update-after-land exit non-zero"
    warning: "This script uses fail-open design. Failures must not block landing. See objective-update-after-land.md."
  - action: "resolving plan or objective metadata after the merge pipeline runs"
    warning: "Capture plan_id and objective_number BEFORE pipeline execution. The pipeline deletes the branch, making branch-based resolution impossible afterward."
    score: 6
  - action: "using only branch-based discovery for plan/objective resolution"
    warning: "Use direct lookup with --plan parameter when available. Branch-based discovery fails if the branch is already deleted. Direct lookup with fallback is the resilient pattern."
    score: 6
---

# Objective Update After Land

After landing a PR, the associated objective issue needs updating. This is handled by the `objective-update-after-land` exec script.

## Location

`src/erk/cli/commands/exec/scripts/objective_update_after_land.py`

## Fail-Open Design

The script always exits 0. The merge has already succeeded at this point — objective update failures must not block the landing workflow.

**Rationale**: The merge is the critical operation; objective tracking is secondary. A failed objective update can always be retried manually.

## How It Works

1. Click command takes three required options (`--objective`, `--pr`, `--branch`) and one optional (`--plan-number`)
2. Delegates to `run_objective_update_after_land()` in `objective_helpers.py`
3. The helper builds a command string for the `/erk:system:objective-update-with-landed-pr` slash command
4. Executes via `stream_command_with_feedback()` with `permission_mode="edits"` and `dangerous=True`
5. Returns `CommandResult` — handles both success and error cases without raising

## Context Capture Before Pipeline Execution

The land pipeline captures plan and objective metadata **before** executing the merge pipeline, which deletes the feature branch. After branch deletion, the branch-to-plan/objective relationship can no longer be resolved.

<!-- Source: src/erk/cli/commands/land_cmd.py -->

The land command captures `plan_id` and `objective_number` before the merge pipeline runs. These are discovered via branch-based lookup and then passed to the post-merge objective update step, ensuring the metadata is available even after the branch is deleted.

## Direct Lookup with Fallback

The `objective_apply_landed_update` exec script supports a `--plan` parameter for direct lookup. When provided, it skips branch-based plan discovery entirely. This is the resilient path — branch-based discovery can fail if the branch has already been deleted.

<!-- Source: src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py -->

Fallback chain in `objective_apply_landed_update.py`:

1. If `--plan` is provided, use it directly
2. Otherwise, discover plan via `plan_backend.get_plan_for_branch()`
3. Auto-fill objective from `plan_result.objective_id` if not explicitly provided
4. Auto-fill PR from `github.get_pr_for_branch()` if not explicitly provided

## Activation

Called from the land pipeline after a successful merge. The land pipeline invokes this as a post-merge step.

## Related Topics

- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Related error handling patterns
- [Exec Command Consolidation](../objectives/exec-command-consolidation.md) - The consolidated exec script pattern

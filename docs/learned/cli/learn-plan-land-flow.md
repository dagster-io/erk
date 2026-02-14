---
title: Learn Plan Land Flow
read_when:
  - "landing PRs associated with learn plans"
  - "understanding how learn plan metadata updates parent issues"
tripwires:
  - action: "landing a PR without updating associated learn plan status"
    warning: "Learn plan PRs trigger special execution pipeline steps that update parent plan metadata. Ensure check_learn_status, update_learn_plan, and close_review_pr steps execute after merge."
last_audited: "2026-02-08"
audit_result: edited
---

# Learn Plan Land Flow

When landing a PR from a learn plan branch, the land execution pipeline runs additional steps that update the parent plan's metadata and promote tripwire candidates. This document explains **why** learn plans need special handling and how the pipeline orchestrates these post-merge operations.

## Why Learn Plans Need Special Pipeline Steps

**The core problem**: Learn plans document insights from implementation sessions. The parent plan (the feature that was implemented) needs to track when its documentation has landed.

**Without special handling**, these metadata updates would be manual:

- Engineers would manually update parent issue status after landing docs
- No visibility into which plans have completed their learning cycle

**The solution**: The execution pipeline detects learn plan branches and runs additional steps after merge:

1. **Update parent plan metadata**: Set `learn_status = plan_completed` and record the PR number
2. **Close review PR**: Clean up any associated review PR

## How Learn Plan Detection Works

<!-- Source: src/erk/cli/commands/land_pipeline.py, check_learn_status() step -->

The validation pipeline's `check_learn_status()` step extracts the issue number from the branch name prefix. If a plan issue exists for that number, it triggers downstream execution steps. See `check_learn_status()` in `src/erk/cli/commands/land_pipeline.py`.

**Why extract from branch name instead of PR labels?**

Branch names are stable identifiers (set at `erk prepare` time). PR labels can be added/removed during review. Extracting from branch name means learn plan detection is deterministic—the same branch will always trigger the same pipeline steps.

**Detection sequence**:

1. `extract_leading_issue_number(state.branch)` → `123` from `P123-feature-branch`
2. Check if issue #123 exists
3. Optionally prompt user to trigger async learn (if not already learned)
4. Populate `state.plan_issue_number` for execution pipeline

## Execution Pipeline Steps for Learn Plans

<!-- Source: src/erk/cli/commands/land_pipeline.py, _execution_pipeline() -->

After the PR merges, the execution pipeline runs learn-specific steps in this order. See `_execution_pipeline()` in `src/erk/cli/commands/land_pipeline.py`.

**Why this ordering?**

1. **`merge_pr`** (standard) — Merge first; if this fails, no cleanup needed
2. **`update_objective`** (standard) — Update objective before learn plan (objective more critical)
3. **`update_learn_plan`** — Update parent plan's `learn_status` field
4. **`close_review_pr`** — Close associated review PR if exists
5. **`cleanup_and_navigate`** (standard) — Delete branches and navigate

**Why learn plan updates come after objective updates**: Objective tracking is higher priority than learning metadata. If execution fails partway through, we prefer to have updated the objective rather than the learn status.

## Parent Plan Metadata Update

<!-- Source: src/erk/cli/commands/land_pipeline.py, update_learn_plan() step -->

The `update_learn_plan()` step reads the `learned_from_issue` field from the current plan and updates that parent plan's issue body. See `update_learn_plan()` in `src/erk/cli/commands/land_pipeline.py`.

**Why update a different issue's body?**

Learn plans are child plans (they document parent features). The parent plan issue is the canonical place to track learning status. Updating the parent creates a bidirectional link:

- Parent → Learn: `learn_plan_pr: 456` (PR that implemented the docs)
- Learn → Parent: `learned_from_issue: 123` (feature that was documented)

**Fail-open pattern**: If the parent issue doesn't exist or the `learned_from_issue` field is missing, the step silently returns. This prevents land failures when metadata is malformed or deleted.

**Critical fields updated**:

```yaml
# In parent plan issue body
learn_status: plan_completed # Was: completed_with_plan
learn_plan_pr: 456 # The landed PR number
```

## Review PR Cleanup

<!-- Source: src/erk/cli/commands/land_pipeline.py, close_review_pr() step -->

Learn plans may have associated review PRs (created via `erk plan review`). The `close_review_pr()` step closes these PRs after the implementation lands. See `close_review_pr()` in `src/erk/cli/commands/land_pipeline.py`.

**Why close review PRs automatically?**

Review PRs exist to discuss the plan before implementation. Once the implementation lands, the review is obsolete. Manual cleanup would be tedious and error-prone (engineers forget to close stale reviews).

**Detection mechanism**: The step calls `cleanup_review_pr()` which searches for review PRs linked to the plan issue number.

**Fail-open pattern**: If no review PR exists or closing fails, the step silently continues. Review PR cleanup is non-critical—the implementation already landed.

## State Field Threading

<!-- Source: src/erk/cli/commands/land_pipeline.py, LandState dataclass -->

The `LandState` dataclass threads `plan_issue_number` through the validation and execution pipelines. See the `LandState` definition in `src/erk/cli/commands/land_pipeline.py`.

**Why thread through state instead of re-computing in each step?**

Validation extracts the issue number once and validates it exists. Execution steps assume validation passed and use the cached issue number. This avoids redundant GitHub API calls and ensures all steps operate on the same issue.

**Population lifecycle**:

1. **Validation pipeline**: `check_learn_status()` extracts from branch name → `state.plan_issue_number`
2. **Shell script boundary**: Issue number serialized as flag (if available)
3. **Execution pipeline**: `make_execution_state()` re-derives from branch name → `state.plan_issue_number`

**Why re-derive during execution?**

The shell script boundary is minimal (PR number, branch name, basic flags). Re-deriving the issue number from the branch name ensures execution state matches current branch state, even if the branch was modified between validation and execution.

## When Learn Plan Steps Are Skipped

All learn-specific steps check `state.plan_issue_number` and skip execution if `None`. This happens when:

- Branch name doesn't have an issue prefix (e.g., `feature-branch` not `P123-feature-branch`)
- Issue doesn't exist on GitHub (deleted or never created)
- Execution was invoked manually without a plan context

**Why fail-open instead of fail-closed?**

Not every branch is a plan branch. Regular feature branches should land normally without triggering learn plan logic. Checking `plan_issue_number is None` makes the pipeline generic—it handles both plan and non-plan branches.

## Comparison to Objective Updates

Both learn plans and objectives use the execution pipeline for post-merge updates, but they differ in criticality:

| Aspect             | Learn Plan Updates              | Objective Updates         |
| ------------------ | ------------------------------- | ------------------------- |
| **Criticality**    | Advisory metadata               | High-value tracking       |
| **Failure mode**   | Fail-open (continue if missing) | Prompt user to retry      |
| **Update target**  | Parent plan issue               | Objective issue           |
| **Pipeline order** | After objective updates         | Before learn plan updates |

**Why objectives come first**: If execution fails partway through, we prefer to have updated the objective (which tracks high-level progress) rather than the learn metadata (which is auxiliary documentation tracking).

## Related Documentation

- [Linear Pipelines](../architecture/linear-pipelines.md) - Two-pipeline pattern and step sequencing
- [Land State Threading](../architecture/land-state-threading.md) - Immutable state management through pipelines
- [Learn Workflow](../planning/learn-workflow.md) - Complete learn plan lifecycle from creation to landing
- [Tripwire Promotion Patterns](../planning/tripwire-promotion-patterns.md) - Extracting and promoting tripwires from learn plans

---
title: Learn Plans vs. Implementation Plans
read_when:
  - "choosing between plan types"
  - "creating erk-learn plans"
  - "understanding how learn plans relate to implementation plans"
  - "debugging learn plan base branch selection"
tripwires:
  - action: "creating a learn plan without setting learned_from_issue"
    warning: "Learn plans MUST set learned_from_issue to their parent implementation plan's issue number. Without it, base branch auto-detection fails and the learn plan lands on trunk instead of stacking on the parent."
  - action: "running /erk:learn on an issue that already has the erk-learn label"
    warning: "Learn plans cannot generate additional learn plans — this creates documentation cycles. The learn command validates this upfront and rejects learn-on-learn."
  - action: "manually setting the base branch for a learn plan submission"
    warning: "Learn plan base branch is auto-detected from learned_from_issue → parent branch. Only use --base to override if the parent branch is missing from the remote."
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
---

# Learn Plans vs. Implementation Plans

Erk has two plan types that share the same issue infrastructure (`erk-plan` label, plan-header metadata, same lifecycle phases) but serve fundamentally different purposes. Understanding when to use each — and how they connect — prevents workflow mistakes and ensures documentation is created alongside the code it documents.

## Decision Table

**Ask: "Is the primary output code or documentation?"**

| Signal                                    | Plan Type      | Label(s)                 | Typical Output              |
| ----------------------------------------- | -------------- | ------------------------ | --------------------------- |
| Adding features, fixing bugs, refactoring | Implementation | `erk-plan`               | Source code, tests, config  |
| Extracting insights from completed work   | Learn          | `erk-plan` + `erk-learn` | Docs in `docs/learned/`     |
| Consolidating learnings from multiple PRs | Learn          | `erk-plan` + `erk-learn` | Docs, tripwires, checklists |

## Why Two Types Exist

Implementation plans produce code changes. But the insights gained during implementation — patterns discovered, anti-patterns avoided, architectural decisions made — are valuable to future agents and would be lost without a structured extraction step.

Learn plans exist to capture those insights as documentation. They are intentionally separate from implementation plans because:

1. **Different base branches** — Learn plans stack on the parent implementation branch so documentation ships alongside the code it describes. Implementation plans branch from trunk.
2. **Different triggering** — Learn plans are created _after_ implementation (manually via `/erk:learn` or automatically via async workflow), not before.
3. **Cycle prevention** — A learn plan cannot generate another learn plan. The `/erk:learn` command validates this upfront by checking for the `erk-learn` label.

## The `learned_from_issue` Link

The key structural difference between the two plan types is a single plan-header field: `learned_from_issue`. This field exists only on learn plans and points back to the parent implementation plan's issue number.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py, LEARNED_FROM_ISSUE -->

See the `LEARNED_FROM_ISSUE` constant and `PlanHeaderFieldName` type in `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`.

This field drives three behaviors:

1. **Base branch auto-detection** — During `erk plan submit`, the submit command reads `learned_from_issue`, fetches the parent issue, extracts its `branch_name`, and uses that as the base branch. This creates a stacked branch hierarchy: trunk → implementation branch → learn plan branch.

2. **Learn status tracking** — When a learn plan's PR lands, `erk land` reads `learned_from_issue` to find the parent and updates the parent's `learn_status` to `plan_completed` with the learn plan's PR number.

3. **Cycle detection** — `/erk:learn` checks for `erk-learn` label before proceeding, preventing learn-on-learn chains.

<!-- Source: src/erk/cli/commands/submit.py, get_learn_plan_parent_branch -->

See `get_learn_plan_parent_branch()` in `src/erk/cli/commands/submit.py` for the base branch resolution logic with its fallback to trunk.

<!-- Source: src/erk/cli/commands/land_cmd.py, _update_parent_learn_status_if_learn_plan -->

See `_update_parent_learn_status_if_learn_plan()` in `src/erk/cli/commands/land_cmd.py` for the landing-time parent update.

## Branch Stacking Model

```
trunk (main/master)
    └── P123-feature-branch (implementation plan)
            └── P456-docs-for-feature (learn plan, stacked via learned_from_issue)
```

**Why stack instead of branching from trunk?** Documentation should be reviewed alongside the code it describes. Stacking ensures the learn plan's PR diff only shows documentation changes, not a confusing mix of code and docs from different base points.

**Fallback behavior**: If the parent branch lookup fails (parent issue not found, no `branch_name` set, or parent branch missing from remote), learn plan submission falls back to trunk with a warning. This prevents blocking documentation work when the parent state is incomplete.

## Learn Status Lifecycle

The parent implementation plan tracks its learn status through a progression of states:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py, LearnStatusValue -->

See `LearnStatusValue` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` for the valid status values and their docstring.

| Status                 | Meaning                           | Set by                                             |
| ---------------------- | --------------------------------- | -------------------------------------------------- |
| `null` / `not_started` | No learn workflow has run         | Default                                            |
| `pending`              | Learn workflow in progress        | Async learn workflow                               |
| `completed_no_plan`    | Learn ran, no docs needed         | `/erk:learn` (validation found nothing actionable) |
| `completed_with_plan`  | Learn ran, plan issue created     | `/erk:learn` (saved plan issue)                    |
| `pending_review`       | Documentation PR created directly | Direct doc PR workflow                             |
| `plan_completed`       | Learn plan implemented and landed | `erk land` (when learn plan PR merges)             |

**Landing guard**: `erk land` checks `learn_status` before merging an implementation plan's PR. If status is `null`/`not_started` and sessions exist, it warns the user and offers to trigger async learn. Learn plans themselves are skipped in this check — they don't need to be "learned from."

## Anti-Patterns

**Creating a learn plan manually without `--learned-from-issue`**: The `learned_from_issue` field is what distinguishes a learn plan from an implementation plan in the plan-header. Without it, base branch detection defaults to trunk, status tracking breaks, and the TUI can't show the link between plans.

**Running `/erk:learn` on a learn plan issue**: Creates a documentation cycle. The learn command rejects this with a clear error.

**Overriding `--base` on learn plan submission without reason**: The auto-detected parent branch is almost always correct. Override only when the parent branch has been deleted from the remote.

## Related Documentation

- [Plan Lifecycle](lifecycle.md) — Full plan workflow from creation to merge, including learn plan base branch selection details
- [Learn Command](../../../.claude/commands/erk/learn.md) — The `/erk:learn` pipeline that creates learn plans

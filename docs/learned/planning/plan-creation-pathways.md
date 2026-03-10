---
title: Plan Creation Pathways
read_when:
  - "understanding how plans are created in erk"
  - "adding a new plan creation entry point"
  - "debugging which code path created a plan"
---

# Plan Creation Pathways

Plans can be created through multiple entry points, all routing to the planned-PR backend.

## Entry Points

| Entry Point                             | Backend Used                    | Creates            |
| --------------------------------------- | ------------------------------- | ------------------ |
| `/erk:plan-save`                        | Planned PR (PlannedPRBackend)   | Draft pull request |
| `erk pr create --file <path>`           | Planned PR (PlannedPRBackend)   | Draft pull request |
| One-shot dispatch (`one_shot_dispatch`) | Planned PR (`ctx.plan_backend`) | Draft pull request |
| `PlannedPRBackend.create_plan()`        | Planned PR                      | Draft pull request |
| `register_one_shot_plan`                | Planned PR (updates existing)   | Updates skeleton   |

## Backend Routing

The plan backend is hardcoded to `"planned_pr"`. All plan creation routes through PlannedPRBackend. The former dynamic backend selection via `get_plan_backend()` was removed in PR #7971 (objective #7911 node 1.1).

The `ERK_PLAN_BACKEND` environment variable is no longer read by application code.

## Label Application

<!-- Source: packages/erk-shared/src/erk_shared/plan_utils.py, get_title_tag_from_labels -->

All plan creation pathways apply a title tag via `get_title_tag_from_labels()` in `packages/erk-shared/src/erk_shared/plan_utils.py`:

- `"erk-learn"` label → `[erk-learn]` prefix
- All other plans → `[erk-pr]` prefix

## Lifecycle Stage at Creation

Plans are created with `lifecycle_stage: planned` by default. The exception is one-shot plans, which start at `prompted` (set by `one_shot_dispatch`) and transition to `planning` when the agent begins.

## Related Documentation

- [Plan Lifecycle](lifecycle.md) — Full lifecycle from creation through merge
- [Planned PR Backend](planned-pr-backend.md) — Planned PR backend details
- [Plan Title Prefix System](plan-title-prefix-system.md) — Title prefixing behavior

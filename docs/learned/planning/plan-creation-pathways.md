---
title: Plan Creation Pathways
read_when:
  - "understanding how plans are created in erk"
  - "adding a new plan creation entry point"
  - "debugging which code path created a plan"
---

# Plan Creation Pathways

Plans can be created through multiple entry points, each routing to the appropriate backend (issue-based or draft-PR).

## Entry Points

| Entry Point                             | Backend Used                   | Creates                |
| --------------------------------------- | ------------------------------ | ---------------------- |
| `/erk:plan-save`                        | Depends on `ERK_PLAN_BACKEND`  | Issue or draft PR      |
| `erk plan create --file <path>`         | Issue-based (GitHubPlanStore)  | GitHub issue           |
| `erk exec plan-save-to-issue`           | Issue-based (GitHubPlanStore)  | GitHub issue           |
| One-shot dispatch (`one_shot_dispatch`) | Issue-based (GitHubPlanStore)  | Skeleton issue         |
| `DraftPRPlanBackend.create_plan()`      | Draft-PR                       | Draft pull request     |
| `GitHubPlanStore.create_plan()`         | Issue-based                    | GitHub issue           |
| `register_one_shot_plan`                | Issue-based (updates existing) | Updates skeleton issue |

## Backend Routing

Backend selection is controlled by `ERK_PLAN_BACKEND` environment variable:

- `"github"` (default): Routes to `GitHubPlanStore`
- `"draft_pr"`: Routes to `DraftPRPlanBackend`

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/__init__.py, get_plan_backend -->

The `get_plan_backend()` function in `packages/erk-shared/src/erk_shared/plan_store/__init__.py` reads this variable.

## Label Application

<!-- Source: packages/erk-shared/src/erk_shared/plan_utils.py, get_title_tag_from_labels -->

All plan creation pathways apply a title tag via `get_title_tag_from_labels()` in `packages/erk-shared/src/erk_shared/plan_utils.py`:

- `"erk-learn"` label → `[erk-learn]` prefix
- All other plans → `[erk-plan]` prefix

## Lifecycle Stage at Creation

Plans are created with `lifecycle_stage: planned` by default. The exception is one-shot plans, which start at `prompted` (set by `one_shot_dispatch`) and transition to `planning` when the agent begins.

## Related Documentation

- [Plan Lifecycle](lifecycle.md) — Full lifecycle from creation through merge
- [Draft PR Plan Backend](draft-pr-plan-backend.md) — Draft-PR backend details
- [Plan Title Prefix System](plan-title-prefix-system.md) — Title prefixing behavior

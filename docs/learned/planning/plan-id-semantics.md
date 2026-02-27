---
title: Plan ID Semantics
read_when:
  - "calling github.get_pr() or github.get_issue() with a plan_id"
  - "writing code that handles both issue-based and planned-PR plans"
  - "debugging 404 errors when fetching plan metadata"
tripwires:
  - action: "calling gh issue view with a plan_id from PlannedPRBackend"
    warning: "For planned-PR plans, plan_id is a PR number, not an issue number. Use gh pr view instead. Check provider type before assuming plan_id semantics."
---

# Plan ID Semantics

The meaning of `plan_id` depends on which backend created the plan.

## Backend → plan_id Mapping

| Backend          | Provider Name     | plan_id Refers To | Fetch With                          |
| ---------------- | ----------------- | ----------------- | ----------------------------------- |
| PlannedPRBackend | `github-draft-pr` | PR number         | `github.get_pr(repo_root, plan_id)` |

## Why This Matters

For planned-PR plans, the plan content lives in a draft PR body — not a separate issue. Callers working with planned-PR plans can call `github.get_pr(plan_id)` directly without extracting metadata first.

## Detection Pattern

```python
# From setup_impl_from_pr.py
pr_result = github.get_pr(repo_root, plan_number)
if isinstance(pr_result, PRNotFound):
    # Handle missing plan
```

## Provider Name Check

Use `plan_backend.get_provider_name()` for backend-conditional logic:

```python
backend_name = ctx.plan_backend.get_provider_name()
is_planned_pr = backend_name == "github-draft-pr"
```

Do not use `isinstance` checks — the provider name string is the stable API.

## Related Documentation

- [Planned PR Backend](planned-pr-backend.md) — Full backend documentation
- [Plan Creation Pathways](plan-creation-pathways.md) — Entry points and backend routing

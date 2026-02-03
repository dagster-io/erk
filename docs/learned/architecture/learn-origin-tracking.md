---
title: Learn Origin Tracking
read_when:
  - "understanding how learn PRs are identified"
  - "modifying erk land behavior"
  - "working with erk-skip-learn label"
last_audited: "2026-02-03"
audit_result: edited
---

# Learn Origin Tracking

PRs that originate from learn plans need to be identified during `erk land` to prevent infinite extraction loops.

## The Problem

When a PR is landed via `erk land`, the command normally queues the worktree for "pending learn". However, PRs that originate from learn plans should not trigger another extraction cycle:

1. Learn plan creates documentation PR
2. PR lands → queued for learn
3. Extraction runs → finds documentation changes → creates new learn plan
4. Repeat forever

## Skip Mechanisms

| Mechanism                     | Scope  | How Applied                                 |
| ----------------------------- | ------ | ------------------------------------------- |
| `erk-skip-learn` label        | Per-PR | Automatic for learn-originated PRs          |
| `prompt_learn_on_land` config | Global | `erk config set prompt_learn_on_land false` |

## Design Decision: Labels over Body Markers

**Previous approach** (deprecated): A marker string in PR bodies.

**Current approach**: The `erk-skip-learn` GitHub label.

**Rationale**: Labels are visible in GitHub UI, simpler to check, and can be manually added/removed for edge cases.

## Implementation Flow

### PR Creation

When creating a PR from a learn plan (`submit.py`, `finalize.py`):

- Check `plan_type` field in plan-header metadata or `.impl/plan.md`
- If learn plan, add `erk-skip-learn` label via `github.add_label_to_pr()`

### PR Landing

When landing a PR (`land_cmd.py`):

- Check for `erk-skip-learn` label via `github.has_pr_label()`
- If present: skip pending-learn, delete worktree immediately
- If absent: normal flow — mark for pending learn

## Gateway Methods

The `add_label_to_pr()` and `has_pr_label()` methods follow the standard ABC/Real/Fake/DryRun pattern in `packages/erk-shared/src/erk_shared/gateway/github/`.

## Related Documentation

- [Glossary: erk-skip-learn](../glossary.md#erk-skip-learn)
- [Erk Architecture Patterns](erk-architecture.md) - Four-layer integration pattern
- [Plan Lifecycle](../planning/lifecycle.md) - Full plan workflow

---
title: Plan Title Prefix System
read_when:
  - "working with PR titles for plan implementations"
  - "understanding the planned/ prefix on PR titles"
  - "debugging why a PR title has or lacks the planned/ prefix"
---

# Plan Title Prefix System

Plan-linked PRs use a `planned/` prefix in their title to distinguish them from regular PRs at a glance. The prefix is managed by a constant and applied idempotently across three independent code paths.

## Constant

`PLANNED_PR_TITLE_PREFIX = "planned/"` is defined in `src/erk/cli/constants.py:13`.

## Three Code Paths

The prefix is applied in three places, each serving a different submission flow:

<!-- Source: src/erk/cli/commands/submit.py, _add_planned_prefix -->
<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _add_planned_prefix -->
| File                                         | Symbol                  | When Used                                     |
| -------------------------------------------- | ----------------------- | --------------------------------------------- |
| `src/erk/cli/commands/submit.py`             | `_add_planned_prefix()` | Direct `erk submit` command                   |
| `src/erk/cli/commands/pr/submit_pipeline.py` | `_add_planned_prefix()` | `erk pr submit` pipeline                      |
| `.claude/commands/erk/git-pr-push.md`        | Slash command template  | `/erk:git-pr-push` (non-Graphite PR creation) |

## Idempotency Pattern

All three implementations check `title.startswith(PLANNED_PR_TITLE_PREFIX)` before applying, making the prefix application idempotent. This prevents double-prefixing when a PR title is rewritten or resubmitted.

## Intentional Duplication

The `_add_planned_prefix()` function exists in both `submit.py` and `submit_pipeline.py`. This is intentional — the two modules operate in different command flows with different state threading patterns, and sharing the function would create an undesirable coupling. The slash command uses a shell-level check (`planned/${pr_title}`) for the same reason.

## Title Tag vs Title Prefix

Two separate systems modify PR titles:

- **Title tag**: `[erk-plan]` or `[erk-learn]` — added by `get_title_tag_from_labels()` in `packages/erk-shared/src/erk_shared/plan_utils.py:178-190`. This identifies the plan type.
- **Title prefix**: `planned/` — added by `_add_planned_prefix()`. This signals that the PR is an active plan implementation.

Both can apply simultaneously, producing titles like `planned/[erk-plan] My Feature`.

## Related Documentation

- [Draft PR Plan Backend](draft-pr-plan-backend.md) — Backend that uses title prefixing
- [PR Submit Pipeline](../cli/pr-submit-pipeline.md) — Pipeline that applies the prefix

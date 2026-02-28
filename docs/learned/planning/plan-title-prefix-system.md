---
title: Plan Title Prefix System
read_when:
  - "working with PR titles for plan implementations"
  - "understanding the plnd/ prefix on PR titles"
  - "debugging why a PR title has or lacks the plnd/ prefix"
---

# Plan Title Prefix System

Plan-linked PRs use a `plnd/` prefix in their title to distinguish them from regular PRs at a glance. The prefix is managed by a constant and applied idempotently across two independent code paths.

## Constant

`PLANNED_PR_TITLE_PREFIX = "plnd/"` is defined in `src/erk/cli/constants.py` (the `PLANNED_PR_TITLE_PREFIX` constant).

## Two Code Paths

The prefix is applied in two places, each serving a different submission flow:

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _add_planned_prefix -->

| File                                         | Symbol                  | When Used                                     |
| -------------------------------------------- | ----------------------- | --------------------------------------------- |
| `src/erk/cli/commands/pr/submit_pipeline.py` | `_add_planned_prefix()` | `erk pr submit` pipeline                      |
| `.claude/commands/erk/git-pr-push.md`        | Slash command template  | `/erk:git-pr-push` (non-Graphite PR creation) |

## Idempotency Pattern

The Python implementation (`_add_planned_prefix()` in `submit_pipeline.py`) checks `title.startswith(PLANNED_PR_TITLE_PREFIX)` before applying, making the prefix application idempotent. This prevents double-prefixing when a PR title is rewritten or resubmitted.

**Exception:** The slash command `.claude/commands/erk/git-pr-push.md` blindly prepends `plnd/` without checking for an existing prefix. If the command is run twice on the same PR, it will produce `plnd/plnd/...`. This is acceptable because the slash command is only invoked once per PR lifecycle (during initial PR creation), not during resubmission flows.

## Title Tag vs Title Prefix

Two separate systems modify PR titles:

- **Title tag**: `[erk-plan]` or `[erk-learn]` — added by `get_title_tag_from_labels()` in `packages/erk-shared/src/erk_shared/plan_utils.py`. This identifies the plan type.
- **Title prefix**: `plnd/` — added by `_add_planned_prefix()`. This signals that the PR is an active plan implementation.

Both can apply simultaneously, producing titles like `plnd/[erk-plan] My Feature`.

## Related Documentation

- [Draft PR Plan Backend](draft-pr-plan-backend.md) — Backend that uses title prefixing
- [PR Submit Pipeline](../cli/pr-submit-pipeline.md) — Pipeline that applies the prefix

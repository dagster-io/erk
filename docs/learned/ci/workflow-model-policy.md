---
title: Workflow Model Policy
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
read_when:
  - "creating or modifying GitHub Actions workflows that invoke Claude"
  - "choosing which Claude model to use in a workflow"
  - "understanding why all workflows default to Opus"
tripwires:
  - action: "creating workflows that invoke Claude without specifying model"
    warning: "All workflows MUST default to claude-opus-4-6. See workflow-model-policy.md for the standardization rationale."
---

# Workflow Model Policy

All erk GitHub Actions workflows that invoke Claude MUST default to `claude-opus-4-6`. This standardization was completed across all 6 Claude-invoking workflows to ensure consistent behavior and eliminate per-workflow model selection confusion.

## Affected Workflows

| Workflow               | Model Parameter           | Default           |
| ---------------------- | ------------------------- | ----------------- |
| `ci.yml`               | Direct reference          | `claude-opus-4-6` |
| `learn.yml`            | Direct reference          | `claude-opus-4-6` |
| `one-shot.yml`         | `model_name` input        | `claude-opus-4-6` |
| `plan-implement.yml`   | `model_name` input (dual) | `claude-opus-4-6` |
| `pr-address.yml`       | `model_name` input        | `claude-opus-4-6` |
| `pr-fix-conflicts.yml` | `model_name` input        | `claude-opus-4-6` |

Workflows without Claude invocation (`docs.yml`, `code-reviews.yml`) are not affected.

## Review Models Are NOT Standardized

The `.erk/reviews/` directory contains review configurations that intentionally use cost-optimized models:

| Review Config                  | Model               | Rationale                       |
| ------------------------------ | ------------------- | ------------------------------- |
| `audit-pr-docs.md`             | `claude-sonnet-4-6` | Balanced cost vs reasoning      |
| `dignified-python.md`          | `claude-haiku-4-5`  | Pattern matching is lightweight |
| `tripwires.md`                 | `claude-sonnet-4-5` | Balanced cost vs reasoning      |
| `test-coverage.md`             | `claude-haiku-4-5`  | Coverage checks are mechanical  |
| `dignified-code-simplifier.md` | `claude-haiku-4-5`  | Simplification is lightweight   |

Review models are chosen per-review based on task complexity, not standardized to Opus.

## Dual-Default Pattern in plan-implement.yml

`plan-implement.yml` supports both `workflow_dispatch` (manual trigger) and `workflow_call` (programmatic invocation from other workflows like `one-shot.yml`). Both define `model_name` with the same default (`claude-opus-4-6`) but differ in `distinct_id` handling:

- **workflow_dispatch**: `distinct_id` is required (for manual trigger correlation)
- **workflow_call**: `distinct_id` is optional with default `"called"` (caller may or may not need correlation)

## Related Documentation

- [GitHub Actions Claude Integration](github-actions-claude-integration.md) — Workflow structure and model selection

---
title: Draft-PR Learn Pipeline
read_when:
  - "debugging why erk learn fails for draft-PR-backed plans"
  - "understanding how trigger-async-learn discovers plan IDs for draft-PR plans"
  - "working on the learn pipeline for non-issue-based plans"
---

# Draft-PR Learn Pipeline

The async learn pipeline discovers plan IDs differently for draft-PR plans vs. issue-based plans. This document explains the difference and the fallback behavior.

## The Problem

The original learn pipeline discovered plan IDs via branch name → metadata lookup, which only worked for GitHub Issue-based plans (where the branch name encodes the issue number using the `P{issue}-` prefix). Draft-PR plans use a `plan-` prefix and store the plan ID as the PR number, not an issue number.

## The Fix

When `plan_backend.get_provider_name() == "github-draft-pr"`, `_get_pr_for_plan_direct()` in `trigger_async_learn.py` short-circuits the branch-name discovery step and uses the PR number directly as the plan ID:

```python
# src/erk/cli/commands/exec/scripts/trigger_async_learn.py
if plan_backend.get_provider_name() == "github-draft-pr":
    pr_result = github.get_pr(repo_root, int(plan_id))
```

For issue-based plans, the function falls back to branch-name lookup via `plan_backend.get_metadata_field(repo_root, plan_id, "branch_name")`.

## Metadata Fallback for Gist URL

For draft-PR plans, the gist URL (learn materials location) is stored as a comment on the PR rather than in a metadata block. The land command (`land_cmd.py`) has a comment-based fallback to retrieve this URL when the metadata block lookup returns nothing.

## Affected Files

- `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` — short-circuit for draft-PR plan ID discovery
- `src/erk/cli/commands/pr/land_cmd.py` — comment-based fallback for gist URL retrieval
- `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py` — PR lookup utilities used by the pipeline

## Related Documentation

- [Draft PR Plan Backend](draft-pr-plan-backend.md) — Backend overview and plan ID semantics
- [Draft PR Lifecycle](draft-pr-lifecycle.md) — Full lifecycle including learn trigger
- [Learn Pipeline Workflow](learn-pipeline-workflow.md) — Overall learn pipeline architecture

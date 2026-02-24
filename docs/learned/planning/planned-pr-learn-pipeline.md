---
title: Planned PR Learn Pipeline
read_when:
  - "debugging why erk learn fails for planned-PR-backed plans"
  - "understanding how trigger-async-learn discovers plan IDs for planned-PR plans"
  - "working on the learn pipeline for non-issue-based plans"
---

# Planned PR Learn Pipeline

The async learn pipeline discovers plan IDs differently for planned-PR plans vs. issue-based plans. This document explains the difference and the fallback behavior.

## The Problem

The original learn pipeline discovered plan IDs via branch name → metadata lookup, which only worked for GitHub Issue-based plans (where the branch name encodes the issue number using the `P{issue}-` prefix). Planned PR plans use a `plnd/` prefix and store the plan ID as the PR number, not an issue number.

## The Fix

When the plan backend is `"github-draft-pr"`, the learn trigger in `trigger_async_learn.py` short-circuits the branch-name discovery step and uses the PR number directly as the plan ID.

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py -->

The direct PR lookup logic lives in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`.

For issue-based plans, the function falls back to branch-name lookup via `plan_backend.get_metadata_field(repo_root, plan_id, "branch_name")`.

## Metadata Fallback for Gist URL

For planned-PR plans, the gist URL (learn materials location) is stored as a comment on the PR rather than in a metadata block. The land command (`land_cmd.py`) has a comment-based fallback to retrieve this URL when the metadata block lookup returns nothing.

## Affected Files

- `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` — short-circuit for planned-PR plan ID discovery
- `src/erk/cli/commands/pr/land_cmd.py` — comment-based fallback for gist URL retrieval
- `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py` — PR lookup utilities used by the pipeline

## Related Documentation

- [Planned PR Backend](planned-pr-backend.md) — Backend overview and plan ID semantics
- [Planned PR Lifecycle](planned-pr-lifecycle.md) — Full lifecycle including learn trigger
- [Learn Pipeline Workflow](learn-pipeline-workflow.md) — Overall learn pipeline architecture

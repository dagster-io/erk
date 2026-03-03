---
title: Planned PR Learn Pipeline
read_when:
  - "debugging why erk learn fails for planned-PR-backed plans"
  - "understanding how trigger-async-learn discovers plan IDs for planned-PR plans"
  - "working on the learn pipeline"
---

# Planned PR Learn Pipeline

The async learn pipeline discovers plan IDs from the PR number. Plans use the `plnd/` prefix and store the plan ID as the PR number.

## Plan ID Discovery

The learn trigger in `trigger_async_learn.py` uses the PR number directly as the plan ID.

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py -->

The direct PR lookup logic lives in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`.

## Metadata Fallback for Learn Materials Branch

For draft-PR plans, the learn materials location (session branch) is stored as a comment on the PR rather than in a metadata block. The land command (`land_cmd.py`) has a comment-based fallback to retrieve this information when the metadata block lookup returns nothing.

## Affected Files

- `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` — short-circuit for draft-PR plan ID discovery
- `src/erk/cli/commands/land_cmd.py` — comment-based fallback for learn materials retrieval
- `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py` — PR lookup utilities used by the pipeline

## Related Documentation

- [Planned PR Backend](planned-pr-backend.md) — Backend overview and plan ID semantics
- [Planned PR Lifecycle](planned-pr-lifecycle.md) — Full lifecycle including learn trigger
- [Learn Pipeline Workflow](learn-pipeline-workflow.md) — Overall learn pipeline architecture

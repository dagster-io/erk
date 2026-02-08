---
title: GitHub Actions API Interaction Patterns
read_when:
  - "triggering GitHub Actions workflows from erk code"
  - "querying workflow run status from gateway methods"
  - "debugging workflow run discovery or correlation"
  - "choosing between REST and GraphQL for workflow queries"
tripwires:
  - action: "triggering a workflow_dispatch without a distinct_id input"
    warning: "All erk workflows use distinct_id for reliable run correlation. Without it, trigger_workflow cannot find the run ID. See the run-name convention."
  - action: "querying individual workflow runs in a loop"
    warning: "Use get_workflow_runs_by_node_ids for batch queries (GraphQL O(1) vs REST O(N)). See the REST vs GraphQL decision table."
  - action: "adding a new workflow_dispatch workflow without run-name"
    warning: "Every erk workflow must use run-name with distinct_id for trigger_workflow discovery. Pattern: run-name: '<context>:${{ inputs.distinct_id }}'"
last_audited: "2026-02-08"
audit_result: regenerated
---

# GitHub Actions API Interaction Patterns

Erk relies heavily on the GitHub Actions API for its remote execution model — dispatching workflows, tracking run status, and correlating triggers to runs. This document captures the cross-cutting patterns that span the gateway layer, workflow YAML, and CLI commands.

For GitHub Actions YAML syntax (triggers, expressions, permissions), see [GitHub's workflow syntax docs](https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions). For erk-specific workflow composition patterns (compound conditions, step ID mismatches), see `docs/learned/ci/github-actions-workflow-patterns.md`.

## The distinct_id Correlation Problem

GitHub's `workflow_dispatch` API has a fundamental gap: triggering a workflow returns no run ID. The caller knows the workflow was triggered but has no way to find the resulting run. This is because `workflow_dispatch` is asynchronous — the API returns 204 No Content, and the run appears on the server some time later (typically 1-5 seconds, but up to 30+ seconds under load).

Erk solves this with a **distinct_id correlation pattern**:

1. `trigger_workflow` generates a random 6-character base36 ID
2. The ID is injected as a `distinct_id` workflow input
3. Every erk workflow uses `run-name` to embed the ID in its display title
4. `trigger_workflow` polls `gh run list` and matches on `displayTitle` containing `:<distinct_id>`

The `run-name` convention across all erk workflows follows this pattern:

```yaml
# Third-party API pattern: run-name convention for run correlation
run-name: "${{ inputs.issue_number }}:${{ inputs.distinct_id }}"
run-name: "pr-address:#${{ inputs.pr_number }}:${{ inputs.distinct_id }}"
run-name: "rebase:${{ inputs.branch_name }}:${{ inputs.distinct_id }}"
```

The colon-delimited format allows `trigger_workflow` to search for `:<distinct_id>` without false-positive matches on issue numbers or branch names.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealGitHub.trigger_workflow -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/abc.py, GitHub.trigger_workflow -->

See `RealGitHub.trigger_workflow()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py` for the implementation. The polling uses an adaptive delay strategy: 5 fast attempts (1s each), then 10 slower attempts (2s each), totaling ~25 seconds before timeout.

## REST vs GraphQL Decision

The GitHub gateway uses two API surfaces for workflow queries. The choice is driven by query cardinality:

| Scenario | API | Why |
|---|---|---|
| Single run by ID | REST (`actions/runs/{id}`) | Direct lookup, includes `node_id` field |
| List runs for workflow | REST via `gh run list` | Paginated, supports `--user` filter |
| Batch query N runs by node ID | GraphQL `nodes(ids: [...])` | O(1) API call vs O(N) REST calls |
| Run status for multiple branches | REST (fetch all, filter locally) | GraphQL schema lacks branch filtering |

The GraphQL batch pattern is critical for the `erk plan list` command, which shows workflow status for many plans simultaneously. Without batching, displaying 20 plans would require 20 individual REST calls.

**Anti-pattern**: Using `get_workflow_run` in a loop. If you have multiple run IDs, store their GraphQL node IDs and use `get_workflow_runs_by_node_ids` instead.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealGitHub.get_workflow_runs_by_node_ids -->

See `RealGitHub.get_workflow_runs_by_node_ids()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py` for the GraphQL batch implementation. Note the critical `gh api graphql` array syntax: `-f nodeIds[]=val1 -f nodeIds[]=val2` (not JSON-encoded array).

## Workflow Run Priority Selection

When displaying workflow status for a branch (e.g., in `erk plan list`), multiple runs may exist. The gateway selects the "most relevant" run using a priority hierarchy:

1. **Active runs** (in_progress, queued) — the current state matters most
2. **Failed runs** — failures are more actionable than successes
3. **Successful runs** — most recent

This ordering reflects erk's operator-facing design: if something is running, show that; if something failed, surface the failure; only show success as the fallback.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealGitHub.get_workflow_runs_by_branches -->

See `RealGitHub.get_workflow_runs_by_branches()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py` for the full priority logic.

## WorkflowRun Field Availability

The `WorkflowRun` type has fields that vary in availability depending on which API fetched the data. This is a cross-cutting concern that affects any code consuming workflow run data.

| Field | REST API | GraphQL nodes() |
|---|---|---|
| `run_id` | Available | Available (as `databaseId`) |
| `status` | Available | Available (via `checkSuite.status`, requires mapping) |
| `conclusion` | Available | Available (via `checkSuite.conclusion`, requires mapping) |
| `branch` | Available | **Not available** — sentinel raises `AttributeError` |
| `display_title` | Available | **Not available** — sentinel raises `AttributeError` |
| `head_sha` | Available | Available (via `checkSuite.commit.oid`) |
| `node_id` | Available (REST `actions/runs/{id}` only) | Available (as `id`) |

The sentinel pattern (`_NotAvailable`) ensures accessing unavailable fields fails loudly rather than returning None silently. Code consuming `WorkflowRun` objects must know which API path produced them.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/types.py, WorkflowRun -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/types.py, _NotAvailable -->

See `WorkflowRun` and `_NotAvailable` in `packages/erk-shared/src/erk_shared/gateway/github/types.py`.

## Related Documentation

- [GitHub CLI Limits](../architecture/github-cli-limits.md) — GH-API-AUDIT convention, REST pagination for large PRs
- [GitHub Actions Workflow Patterns](../ci/github-actions-workflow-patterns.md) — Compound conditions, step ID coordination
- [Subprocess Wrappers](../architecture/subprocess-wrappers.md) — `run_subprocess_with_context` and `execute_gh_command_with_retry` used by all gateway methods

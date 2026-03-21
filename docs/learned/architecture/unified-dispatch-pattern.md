---
title: Unified Dispatch Pattern
read_when:
  - "working with launch_cmd.py dispatch handlers"
  - "adding a new workflow to erk launch"
  - "understanding how workflows are dispatched via erk"
tripwires:
  - action: "adding a new dispatch handler that does not return (branch_name, run_id)"
    warning: "All PR-targeting dispatch handlers must return (branch_name, run_id) for post-dispatch metadata enrichment. learn and consolidate-learn-plans are exceptions (no branch/run_id needed for metadata). See unified-dispatch-pattern.md."
  - action: "dispatching a workflow directly from the launch command body without a handler"
    warning: "Add a dedicated _dispatch_<workflow> handler function. The handler pattern separates PR lookup, validation, input building, and dispatch. See unified-dispatch-pattern.md."
---

# Unified Dispatch Pattern

`src/erk/cli/commands/launch_cmd.py` implements dispatch for all GitHub Actions workflows via a consistent handler pattern.

## The 7 Dispatch Handlers

All handlers receive `RemoteGitHub + explicit params`. PR-targeting handlers return `(branch_name, run_id)`.

| Handler                             | Returns           | PR Required | Notes                                             |
| ----------------------------------- | ----------------- | ----------- | ------------------------------------------------- |
| `_dispatch_workflow`                | `str` (run_id)    | No          | Generic wrapper; other handlers call it           |
| `_dispatch_pr_rebase`               | `tuple[str, str]` | Yes         | Validates OPEN state; passes squash               |
| `_dispatch_pr_address`              | `tuple[str, str]` | Yes         | Validates OPEN state                              |
| `_dispatch_pr_rewrite`              | `tuple[str, str]` | Yes         | Validates OPEN state                              |
| `_dispatch_learn`                   | `None`            | Yes         | No metadata enrichment                            |
| `_dispatch_one_shot`                | `tuple[str, str]` | Yes         | Also takes prompt string                          |
| `_dispatch_consolidate_learn_plans` | `None`            | No          | Delegates to `dispatch_consolidate_learn_plans()` |

## Handler Signature Pattern

<!-- Source: src/erk/cli/commands/launch_cmd.py, launch -->

PR-targeting handlers follow a consistent pattern: they accept `RemoteGitHub`, owner, repo_name, pr_number, model, and ref, then return a tuple of (branch_name, run_id). See the handler implementations in `src/erk/cli/commands/launch_cmd.py` for concrete examples like `_dispatch_pr_rebase()` and `_dispatch_pr_address()`.

## Handler Implementation Pattern

Each PR-targeting handler follows this sequence:

1. Fetch PR via `remote.get_pr(owner, repo, number)` → check for `RemotePRNotFound`
2. Validate state (`pr.state == "OPEN"`) via `Ensure.invariant()`
3. Display PR info to user
4. Build `inputs: dict[str, str]`
5. Call `_add_optional_model(inputs, model=model)` if model supported
6. Call `_dispatch_workflow(remote, ...)` → get `run_id`
7. Return `(pr.head_ref_name, run_id)`

## `_dispatch_workflow` (Generic Wrapper)

<!-- Source: src/erk/cli/commands/launch_cmd.py, launch -->

The generic workflow dispatcher accepts `RemoteGitHub`, owner, repo_name, workflow_name, inputs dict, and ref. It looks up the workflow filename via `WORKFLOW_COMMAND_MAP`, dispatches via `remote.dispatch_workflow()`, prints the run URL to the user, and returns the run ID for post-dispatch metadata enrichment. See `_dispatch_workflow()` in `src/erk/cli/commands/launch_cmd.py`.

## Post-Dispatch: Metadata Enrichment

<!-- Source: src/erk/cli/commands/launch_cmd.py, launch -->

After a PR-targeting handler completes, the `launch` command updates plan metadata with the dispatch run ID when a local repo is available. This enrichment calls `maybe_update_plan_dispatch_metadata()` with the branch name and run ID returned by the handler. `learn` and `consolidate-learn-plans` handlers don't return `(branch_name, run_id)`, so they skip this metadata enrichment step. See the post-dispatch logic in `src/erk/cli/commands/launch_cmd.py`.

## Ref Resolution

Before dispatch, ref is resolved in priority order:

1. `--ref-current` flag → current branch name
2. `--ref` flag → explicit ref string
3. `ctx.local_config.dispatch_ref` → configured dispatch ref
4. `remote.get_default_branch_name(owner, repo)` → fallback (remote API call)

See [Ref Resolution Patterns](../cli/ref-resolution-patterns.md) for details.

## `plan-implement` Exception

<!-- Source: src/erk/cli/commands/launch_cmd.py, launch -->

The `plan-implement` workflow is blocked at the handler level and raises a `UsageError` directing users to use `erk pr dispatch` instead. This is because the plan-implement workflow requires branch and PR setup that is only handled by the dedicated `erk pr dispatch` command. See the workflow routing logic in `src/erk/cli/commands/launch_cmd.py`.

## Related Documentation

- [Ref Resolution Patterns](../cli/ref-resolution-patterns.md) — dispatch ref resolution
- [Repo Resolution Pattern](../cli/repo-resolution-pattern.md) — `--repo` flag infrastructure
- [Consolidate Learn Plans Workflow](../planning/consolidate-learn-plans-workflow.md) — consolidate-learn-plans dispatch details

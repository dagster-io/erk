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

PR-targeting handlers:

```python
def _dispatch_pr_<name>(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    pr_number: int,
    model: str | None,
    ref: str,
) -> tuple[str, str]:
    """Dispatch <name> workflow. Returns (branch_name, run_id)."""
```

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

```python
def _dispatch_workflow(
    remote: RemoteGitHub,
    *,
    owner: str,
    repo_name: str,
    workflow_name: str,
    inputs: dict[str, str],
    ref: str,
) -> str:  # run_id
```

Looks up workflow filename via `WORKFLOW_COMMAND_MAP`, dispatches via `remote.dispatch_workflow()`, prints run URL, returns run ID.

## Post-Dispatch: Metadata Enrichment

After all handlers complete, the `launch` command calls:

```python
if has_local_repo and branch_name is not None and run_id is not None:
    maybe_update_plan_dispatch_metadata(ctx, ctx.repo, branch_name, run_id)
```

This updates plan metadata with the dispatch run ID when a local repo is available. `learn` and `consolidate-learn-plans` handlers don't return `(branch_name, run_id)`, so they skip this step.

## Ref Resolution

Before dispatch, ref is resolved in priority order:

1. `--ref-current` flag → current branch name
2. `--ref` flag → explicit ref string
3. `ctx.local_config.dispatch_ref` → configured dispatch ref
4. `remote.get_default_branch_name(owner, repo)` → fallback (remote API call)

See [Ref Resolution Patterns](../cli/ref-resolution-patterns.md) for details.

## `plan-implement` Exception

`plan-implement` workflow is blocked at the handler level:

```python
elif workflow_name == "plan-implement":
    raise click.UsageError("Use 'erk pr dispatch' instead...")
```

The plan-implement workflow requires branch and PR setup handled by `erk pr dispatch`.

## Related Documentation

- [Ref Resolution Patterns](../cli/ref-resolution-patterns.md) — dispatch ref resolution
- [Repo Resolution Pattern](../cli/repo-resolution-pattern.md) — `--repo` flag infrastructure
- [Consolidate Learn Plans Workflow](../planning/consolidate-learn-plans-workflow.md) — consolidate-learn-plans dispatch details

---
title: Remote Workflow Command Pattern
read_when:
  - "creating a new remote workflow command"
  - "triggering GitHub Actions from CLI"
  - "building commands like pr-address-remote"
---

# Remote Workflow Command Pattern

This document describes the pattern for creating CLI commands that trigger GitHub Actions workflows remotely, allowing operations to run in CI without local environment setup.

## Overview

Remote workflow commands follow a consistent pattern:

1. Validate preconditions (auth, repo, PR state)
2. Build workflow inputs
3. Trigger the workflow
4. Optionally update plan dispatch metadata
5. Display run URL

## Command Structure

```python
@click.command("action-remote")
@click.argument("pr_number", type=int, required=True)
@click.option("--model", "model_name", type=str, help="Claude model to use.")
@click.pass_obj
def action_remote(ctx: ErkContext, pr_number: int, *, model_name: str | None) -> None:
    """Trigger remote action workflow."""
    # 1. Validate preconditions
    Ensure.gh_authenticated(ctx)
    Ensure.invariant(not isinstance(ctx.repo, NoRepoSentinel), "Not in a git repository")
    repo: RepoContext = ctx.repo  # type: ignore

    # 2. Verify PR exists and is open
    pr = ctx.github.get_pr(repo.root, pr_number)
    Ensure.invariant(not isinstance(pr, PRNotFound), f"PR #{pr_number} not found")
    Ensure.invariant(pr.state == "OPEN", f"PR is {pr.state}, not OPEN")

    # 3. Build workflow inputs
    inputs = {"pr_number": str(pr_number)}
    if model_name is not None:
        inputs["model_name"] = model_name

    # 4. Trigger workflow
    run_id = ctx.github.trigger_workflow(
        repo_root=repo.root,
        workflow="action-workflow.yml",
        inputs=inputs,
    )

    # 5. Update plan dispatch metadata (if applicable)
    maybe_update_plan_dispatch_metadata(ctx, repo, pr.head_ref_name, run_id)

    # 6. Display run URL
    run_url = f"https://github.com/{pr.owner}/{pr.repo}/actions/runs/{run_id}"
    user_output(f"Run URL: {click.style(run_url, fg='cyan')}")
```

## Key Components

### Precondition Validation

Use `Ensure` helpers for consistent error messages:

- `Ensure.gh_authenticated(ctx)` - Verify GitHub CLI is authenticated
- `Ensure.invariant(condition, message)` - Assert conditions with user-friendly errors
- `Ensure.not_none(value, message)` - Unwrap optional values

### Plan Dispatch Metadata

Use the shared helper from `erk.cli.commands.pr.metadata_helpers`:

```python
from erk.cli.commands.pr.metadata_helpers import maybe_update_plan_dispatch_metadata

maybe_update_plan_dispatch_metadata(ctx, repo, branch_name, run_id)
```

This automatically:

- Extracts plan issue number from `P{number}-*` branch names
- Gets workflow run node ID from GitHub API
- Updates plan-header metadata block on the issue
- Skips gracefully if any step doesn't apply

### Workflow Inputs

Inputs are typed as `dict[str, str]` matching GitHub Actions workflow_dispatch inputs.

## Existing Commands

| Command                       | Workflow              | Purpose                         |
| ----------------------------- | --------------------- | ------------------------------- |
| `erk pr address-remote`       | `pr-address.yml`      | Address PR review comments      |
| `erk pr fix-conflicts-remote` | `rebase-workflow.yml` | Rebase with conflict resolution |

## Related Documentation

- [PR Address Workflows](pr-address-workflows.md) - Detailed pr-address workflow docs
- [GitHub API Rate Limits](../architecture/github-api-rate-limits.md) - API considerations

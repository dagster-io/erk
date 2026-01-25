---
title: Metadata Helpers Module
read_when:
  - "updating plan issue dispatch metadata"
  - "working with remote workflow triggers"
  - "understanding P{issue}-pattern branch naming"
  - "tracking GitHub Actions run IDs on plan issues"
---

# Metadata Helpers Module

The `metadata_helpers.py` module provides shared utilities for updating plan issue metadata when triggering remote workflows.

## Location

`src/erk/cli/commands/pr/metadata_helpers.py`

## Purpose

When remote workflows are triggered on branches following the `P{issue_number}-*` naming pattern, the associated plan issue needs metadata updates to track:

- Workflow run ID
- GitHub Actions node ID
- Dispatch timestamp

This module extracts this shared logic used by multiple remote workflow commands.

## Main Function

```python
def maybe_update_plan_dispatch_metadata(
    ctx: ErkContext,
    repo: RepoContext,
    branch_name: str,
    run_id: str,
) -> None:
    """Update plan issue dispatch metadata if branch follows P{issue}-pattern.

    Uses early returns to skip updates when:
    - Branch doesn't match P{issue_number} pattern
    - Workflow run node ID is not available
    - Issue doesn't have a plan-header metadata block
    """
```

## LBYL Pattern

The function uses Look Before You Leap (LBYL) with early returns for graceful skipping:

```python
def maybe_update_plan_dispatch_metadata(...) -> None:
    # Check 1: Branch must follow P{issue} pattern
    issue_number = extract_leading_issue_number(branch_name)
    if issue_number is None:
        return  # Not a plan branch, skip

    # Check 2: Run node ID must be available
    run_node_id = _get_run_node_id(ctx, repo, run_id)
    if run_node_id is None:
        return  # Can't get node ID, skip

    # Check 3: Issue must have plan metadata block
    if not _has_plan_metadata_block(ctx, repo, issue_number):
        return  # Not a plan issue, skip

    # All checks passed - update metadata
    _update_dispatch_metadata(ctx, repo, issue_number, run_id, run_node_id)
```

## Usage

Called after successfully dispatching a remote workflow:

```python
from erk.cli.commands.pr.metadata_helpers import maybe_update_plan_dispatch_metadata

def address_remote(ctx: ErkContext, pr_number: int) -> None:
    # Dispatch the workflow
    run_id = _dispatch_address_workflow(ctx, pr_number)

    # Update plan issue metadata (if applicable)
    maybe_update_plan_dispatch_metadata(
        ctx,
        repo=repo,
        branch_name=pr.head_branch,
        run_id=run_id,
    )
```

## Branch Pattern

The module works with branches following the pattern:

```
P{issue_number}-{description}
```

Examples:

- `P1234-add-feature` → issue #1234
- `P5678-fix-bug-in-parser` → issue #5678

The `extract_leading_issue_number()` utility extracts the issue number from this pattern.

## Metadata Fields Updated

When all checks pass, the following fields are updated on the plan issue:

| Field                | Value                 | Purpose                |
| -------------------- | --------------------- | ---------------------- |
| `dispatch_run_id`    | GitHub Actions run ID | Link to workflow run   |
| `dispatch_node_id`   | GraphQL node ID       | API access to run      |
| `dispatch_timestamp` | ISO timestamp         | When dispatch occurred |

## Related Topics

- [Plan Lifecycle](../planning/lifecycle.md) - Plan issue metadata management
- [PR Optional Learn Flow](../planning/pr-optional-learn-flow.md) - When learn is triggered

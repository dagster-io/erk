# Plan: Eliminate Serial `gh run view` Fetches in `erk ls`

## Problem

`erk ls -a` makes 11 serial `gh run view` calls, each taking ~800-1200ms, adding ~10 seconds total latency.

**Current code** (`src/erk/core/github/real.py:1235-1256`):

```python
def get_workflow_runs_batch(self, repo_root, run_ids):
    result = {}
    for run_id in run_ids:  # Serial loop - the bottleneck
        result[run_id] = self.get_workflow_run(repo_root, run_id)
    return result
```

## Recommended Approach: Single `gh run list` + Filter

All runs we fetch are from the `dispatch-erk-queue-git.yml` workflow. Instead of fetching each run individually, fetch all recent runs from that workflow in ONE call and filter by run_id in memory.

**Filters applied:**

- `--workflow dispatch-erk-queue-git.yml` - Only this workflow's runs
- `--user <current_user>` - Only runs triggered by current user (from `gh auth status`)

**Performance impact:**

- Before: 11 serial `gh run view` calls (~11s)
- After: 1 `gh run list --workflow --user` call (~1s)

## Implementation

### Step 1: Add `user` param to `list_workflow_runs()`

Update `list_workflow_runs()` in ABC and real implementation to accept optional `user` filter:

```python
# In abc.py
@abstractmethod
def list_workflow_runs(
    self, repo_root: Path, workflow: str, limit: int = 50, *, user: str | None = None
) -> list[WorkflowRun]:
    """List workflow runs for a specific workflow, optionally filtered by user."""
    ...

# In real.py - add --user flag when provided
cmd = ["gh", "run", "list", "--workflow", workflow, "--json", "...", "--limit", str(limit)]
if user:
    cmd.extend(["--user", user])
```

### Step 2: Update ABC Interface for `get_workflow_runs_batch()`

Add optional `workflow` and `user` parameters:

```python
@abstractmethod
def get_workflow_runs_batch(
    self, repo_root: Path, run_ids: list[str], *, workflow: str | None = None, user: str | None = None
) -> dict[str, WorkflowRun | None]:
    """Get details for multiple workflow runs by ID.

    If workflow is provided, uses `gh run list --workflow [--user]` to fetch runs
    and filters by run_id in memory (single API call).
    Otherwise falls back to individual `gh run view` calls.
    """
    ...
```

### Step 3: Update Real Implementation of `get_workflow_runs_batch()`

Modify `get_workflow_runs_batch()` in `src/erk/core/github/real.py`:

```python
def get_workflow_runs_batch(
    self, repo_root: Path, run_ids: list[str], *, workflow: str | None = None, user: str | None = None
) -> dict[str, WorkflowRun | None]:
    """Get details for multiple workflow runs by ID."""
    if not run_ids:
        return {}

    # If workflow provided, use efficient batch fetch via gh run list
    if workflow:
        # Fetch recent runs from workflow (single API call)
        all_runs = self.list_workflow_runs(repo_root, workflow, limit=200, user=user)

        # Build lookup by run_id
        runs_by_id = {run.run_id: run for run in all_runs}

        # Return only requested run_ids
        return {run_id: runs_by_id.get(run_id) for run_id in run_ids}

    # Fallback: individual fetch for each run_id (existing behavior)
    result: dict[str, WorkflowRun | None] = {}
    for run_id in run_ids:
        result[run_id] = self.get_workflow_run(repo_root, run_id)
    return result
```

### Step 4: Update Call Site

Modify `plan_list_service.py` to pass workflow and user:

```python
from erk.cli.constants import DISPATCH_WORKFLOW_NAME

# In get_plan_list_data():
# Get current user from gh auth status (already available via check_auth_status())
_, username, _ = self._github.check_auth_status()

runs_by_id = self._github.get_workflow_runs_batch(
    repo_root, run_ids, workflow=DISPATCH_WORKFLOW_NAME, user=username
)
```

### Step 5: Update Fake/DryRun Implementations

Update signatures in:

- `src/erk/core/github/fake.py`
- `src/erk/core/github/dry_run.py`
- `src/erk/core/github/printing.py`
- `packages/erk-shared/src/erk_shared/github/real.py` (stub)

All just need to add `*, workflow: str | None = None, user: str | None = None` parameters.

## Files to Modify

| File                                                | Change                                                                                                  |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `packages/erk-shared/src/erk_shared/github/abc.py`  | Add `user` param to `list_workflow_runs()`, add `workflow`+`user` params to `get_workflow_runs_batch()` |
| `src/erk/core/github/real.py`                       | Add `--user` flag to `list_workflow_runs()`, implement batch fetch in `get_workflow_runs_batch()`       |
| `src/erk/core/github/fake.py`                       | Add parameters (existing behavior fine)                                                                 |
| `src/erk/core/github/dry_run.py`                    | Add parameters, pass through                                                                            |
| `src/erk/core/github/printing.py`                   | Add parameters, pass through                                                                            |
| `packages/erk-shared/src/erk_shared/github/real.py` | Add parameters to stubs                                                                                 |
| `src/erk/core/services/plan_list_service.py`        | Pass workflow name and username                                                                         |

## Edge Cases

**Q: What if a run_id is older than 200 most recent runs?**
A: Returns `None` for that run_id (same as current behavior for missing runs). For active plans, runs should be recent.

**Q: What if workflow name is wrong?**
A: `list_workflow_runs` returns empty list, all run_ids return `None`. Graceful degradation.

# Plan: Show Workflow URL for In-Progress Learn Status

## Summary

When `erk plan view` shows "Status: in progress" for a learn workflow, display the clickable GitHub Actions workflow URL so users can monitor the running workflow.

## Current Behavior

```
─── Learn ───
Status:      in progress
```

## Desired Behavior

```
─── Learn ───
Status:      in progress
Workflow:    https://github.com/dagster-io/erk/actions/runs/12345678
```

## Implementation

### File: `src/erk/cli/commands/plan/view.py`

**1. Add imports** (around line 13):
```python
from erk_shared.github.metadata.schemas import (
    ...
    LEARN_RUN_ID,  # Add this
    ...
)
from erk_shared.github.parsing import (
    construct_workflow_run_url,
    extract_owner_repo_from_github_url,
)
```

**2. Update `_format_header_section()`** (around line 210-211):

After displaying the learn status, add logic to display the workflow URL when status is "pending" and `learn_run_id` is available:

```python
learn_display = _format_learn_state(learn_status_val, learn_plan_issue_int, learn_plan_pr_int)
lines.append(_format_field("Status", learn_display))

# Show workflow URL when learn is in progress
if learn_status_val == "pending":
    learn_run_id_raw = header_info.get(LEARN_RUN_ID)
    if learn_run_id_raw is not None:
        # plan_url is available from outer scope (passed via closure or parameter)
        # Need to construct URL from plan URL + run ID
        ...
```

**3. Pass plan URL to `_format_header_section()`**:

The function needs access to the plan URL to extract owner/repo. Update signature:

```python
def _format_header_section(header_info: dict[str, object], plan_url: str | None) -> list[str]:
```

Then in the Learn section:
```python
if learn_status_val == "pending":
    learn_run_id_raw = header_info.get(LEARN_RUN_ID)
    if learn_run_id_raw is not None and plan_url is not None:
        owner_repo = extract_owner_repo_from_github_url(plan_url)
        if owner_repo is not None:
            workflow_url = construct_workflow_run_url(owner_repo[0], owner_repo[1], str(learn_run_id_raw))
            lines.append(_format_field("Workflow", workflow_url))
```

**4. Update call site** (around line 314):

```python
header_lines = _format_header_section(header_info, plan.url)
```

## Verification

1. Run the new test: `pytest tests/commands/plan/test_view.py::test_view_plan_learn_pending_with_workflow_url -v`
2. Optionally, find a plan with `learn_status: pending` and `learn_run_id` set
3. Run `erk plan view` and confirm the Workflow URL is displayed

## Test Coverage

Add a test to `tests/commands/plan/test_view.py` following the existing pattern from `test_view_plan_learn_status_pending()` (line 517):

```python
def test_view_plan_learn_pending_with_workflow_url() -> None:
    """Test learn status 'pending' with run_id displays workflow URL."""
    issue_body = """<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

` ``yaml

learn_status: pending
learn_run_id: 12345678

` ``
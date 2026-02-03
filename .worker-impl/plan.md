# Plan: Embed Implementation Plan in Remote Queue Draft PRs

## Problem

When plans are submitted to the remote queue via `erk plan submit`, the draft PR body contains only a brief status message. Normal PRs created via `erk pr submit` embed the full implementation plan in a collapsible `<details>` section. The remote queue draft PRs should do the same.

## Change

**File:** `src/erk/cli/commands/submit.py` — `_submit_single_issue()` function

At line 479, where `pr_body` is constructed, append a collapsible plan section using `plan.body` (already fetched at line 446). The section format matches the existing pattern in `submit_pipeline.py:_build_plan_details_section()`:

```python
pr_body = (
    f"**Author:** @{submitted_by}\n"
    f"**Plan:** {issue_ref}\n\n"
    f"**Status:** Queued for implementation\n\n"
    f"This PR will be marked ready for review after implementation completes.\n\n"
    f"## Implementation Plan\n\n"
    f"<details>\n"
    f"<summary><strong>Implementation Plan</strong> (Issue #{issue_number})</summary>\n\n"
    f"{plan.body}\n\n"
    f"
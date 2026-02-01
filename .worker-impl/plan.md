# Make Implementation Plan and Files Changed sections collapsible in PR body

## Changes

### 1. Add markdown header above Implementation Plan collapse

**File:** `src/erk/cli/commands/pr/submit_pipeline.py` (lines 587-599)

Change `_build_plan_details_section()` to emit a `## Implementation Plan` markdown header before the `<details>` block:

```python
parts = [
    "",
    "## Implementation Plan",
    "",
    "<details>",
    f"<summary>Implementation Plan (Issue #{issue_num})</summary>",
    "",
    plan_context.plan_content,
    "",
    "
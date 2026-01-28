---
title: Learn Plan Metadata Preservation
read_when:
  - "working with learn plan metadata"
  - "troubleshooting null learn_status or learn_plan_issue"
  - "transforming Plan objects in pipelines"
  - "understanding created_from_workflow_run_url field"
  - "adding workflow run backlinks to plans"
tripwires:
  - action: "reading learn_plan_issue or learn_status"
    warning: "Verify field came through full pipeline. If null, check if filtered out earlier. Use gateway abstractions; never hand-construct Plan objects."
---

# Learn Plan Metadata Preservation

Learn plans have metadata fields that must survive all pipeline transformations. When these fields become null unexpectedly, data was lost during a transformation stage.

## Critical Metadata Fields

### `learn_status`

Tracks the status of learn plan processing:

- `"pending"` - Learn plan not yet processed
- `"completed"` - Learn plan has been reviewed and documentation created
- `None` - Not a learn plan, or status unknown

### `learn_plan_issue`

For learn plans, the issue number of the original plan that generated this learn plan. Used to link learn plans back to their source implementation.

- `int` - The parent plan's issue number
- `None` - Not a learn plan, or source unknown

### `created_from_workflow_run_url`

GitHub Actions workflow run URL that created this plan. Provides a backlink from the plan issue to the workflow that generated it.

- **Type**: `string` (nullable)
- **When populated**: During GitHub Actions workflow execution (e.g., `learn.yml`)
- **Format**: `https://github.com/{owner}/{repo}/actions/runs/{run_id}`

**URL Construction** (in GitHub Actions):

```yaml
WORKFLOW_RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

**CLI Usage**:

```bash
erk exec plan-save-to-issue --created-from-workflow-run-url "$WORKFLOW_RUN_URL" ...
```

This field enables:

- Debugging failed plan creations by linking to the workflow run
- Tracing provenance of automatically generated plans
- Quick navigation from plan issue to the workflow that created it

### `review_pr`

Tracks the draft PR created for asynchronous plan review.

- **Type**: `int | None`
- **When populated**: By `plan-create-review-pr` command after PR creation
- **Format**: GitHub PR number (positive integer)

**Purpose:**

This field enables programmatic discovery of which draft PR contains the plan's review-ready version. It supports:

- TUI display of review status
- Automated workflows checking if plan has been reviewed
- Navigation from plan issue to review PR

**Important:** The review PR is distinct from any implementation PR. Review PRs are:

- Always created as drafts
- Never merged (for review only)
- Contain plan content, not implementation

**CLI Usage:**

The field is set automatically by:

```bash
erk exec plan-create-review-pr --issue <issue_number>
```

To read the field:

```bash
erk exec get-plan-metadata --issue <issue_number> --field review_pr
```

## Pipeline Stages and Preservation

### GitHub Gateway

The GitHub gateway fetches issue metadata including labels. Learn-related labels:

- `erk-learn` - Marks this as a learn plan
- Custom fields may be stored in issue body metadata block

### Plan Object Construction

When constructing `Plan` objects from API responses, ensure all metadata fields are populated:

- Read from issue body metadata block if present
- Derive from labels if explicit metadata unavailable
- Never leave fields as None if data is available

### Transformation to PlanRowData

The `PlanListService` transforms `Plan` → `PlanRowData`. Metadata must be preserved through this transformation.

### Filtering Operations

Filter operations may create new collections. Ensure filtered results maintain all original fields - don't reconstruct partial objects.

## Anti-Patterns

### Hand-Constructing Plan Objects

```python
# WRONG: Missing metadata fields
plan = Plan(
    issue_number=123,
    title="My Plan",
    # learn_status and learn_plan_issue are missing!
)
```

Always use gateway abstractions that populate all fields from the source data.

### Partial Object Reconstruction

```python
# WRONG: Creating new object without preserving fields
filtered_plan = Plan(
    issue_number=plan.issue_number,
    title=plan.title,
    # Lost: learn_status, learn_plan_issue, etc.
)
```

Instead, use the original object or ensure all fields transfer.

### Filtering Before Enrichment

```python
# WRONG: Filter before learn_status is set
plans = fetch_from_github()
filtered = [p for p in plans if matches_filter(p)]
enriched = add_learn_metadata(filtered)  # Too late!
```

Enrich first, then filter.

## Debugging Null Metadata

When `learn_status` or `learn_plan_issue` is unexpectedly null:

1. **Check GitHub API response**: Does the raw data contain the metadata?

   ```bash
   gh issue view <num> --json body,labels
   ```

2. **Check gateway output**: Is the Plan object populated correctly?

3. **Check transformation**: Does PlanRowData preserve the fields?

4. **Check filtering**: Did a filter stage lose the data?

5. **Check for hand-construction**: Is someone creating Plan objects manually?

## Related Topics

- [Plan Lifecycle](lifecycle.md) - Overall plan state management
- [TUI Plan Title Rendering Pipeline](../tui/plan-title-rendering-pipeline.md) - Data flow through TUI
- [Learn Workflow](learn-workflow.md) - How learn plans are created

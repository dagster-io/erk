---
title: Metadata Field Addition Workflow
read_when:
  - "adding a new field to plan-header metadata"
  - "extending plan issue schema"
  - "coordinating metadata changes across files"
---

# Metadata Field Addition Workflow

Adding a new field to the plan-header metadata block requires coordinated changes across multiple files. This checklist ensures nothing is missed.

## 5-File Coordination Checklist

### 1. schemas.py - Define the Field

**File:** `packages/erk-shared/src/erk_shared/github/metadata/schemas.py`

Add the field name to `PlanHeaderFieldName` type union:

```python
PlanHeaderFieldName = Literal[
    # ... existing fields ...
    "your_new_field",
]
```

Add constant for the field name:

```python
YOUR_NEW_FIELD: Literal["your_new_field"] = "your_new_field"
```

If the field needs validation, add it to `validate_plan_header_data()`:

```python
# Validate optional your_new_field field
if YOUR_NEW_FIELD in data and data[YOUR_NEW_FIELD] is not None:
    if not isinstance(data[YOUR_NEW_FIELD], str):
        raise ValueError("your_new_field must be a string or null")
```

### 2. plan_header.py - Thread the Parameter

**File:** `packages/erk-shared/src/erk_shared/github/metadata/plan_header.py`

Add parameter to `create_plan_header_block()`:

```python
def create_plan_header_block(
    # ... existing params ...
    your_new_field: str | None,
) -> str:
```

Add to the data dict construction:

```python
if your_new_field is not None:
    data[YOUR_NEW_FIELD] = your_new_field
```

Repeat for `create_plan_issue_body()` if it takes the same parameter.

### 3. plan_issues.py - Thread Through Issue Creation

**File:** `packages/erk-shared/src/erk_shared/github/plan_issues.py`

Add parameter to `create_plan_issue()`:

```python
def create_plan_issue(
    # ... existing params ...
    your_new_field: str | None,
) -> CreatePlanIssueResult:
```

Pass to the header creation call:

```python
body = create_plan_issue_body(
    # ... existing args ...
    your_new_field=your_new_field,
)
```

### 4. plan_save_to_issue.py - Add CLI Option

**File:** `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`

Add Click option:

```python
@click.option(
    "--your-new-field",
    default=None,
    help="Description of the field",
)
```

Add parameter to function signature:

```python
def plan_save_to_issue_cmd(
    # ... existing params ...
    your_new_field: str | None,
) -> None:
```

Pass to issue creation:

```python
result = create_plan_issue(
    # ... existing args ...
    your_new_field=your_new_field,
)
```

### 5. Test Fixtures - Update Helpers

**File:** `tests/test_utils/plan_helpers.py`

Add parameter to `make_plan_row()` helper:

```python
def make_plan_row(
    # ... existing params ...
    your_new_field: str | None = None,
) -> PlanRowData:
```

Update any test that constructs Plan objects directly.

## Concrete Example: review_pr Field

The `review_pr` field demonstrates a different pattern: **update-in-place** rather than **creation-time threading**.

### Implementation Approach

Unlike fields that flow through `create_plan_issue()` at creation time, `review_pr` is set **after** the issue already exists:

1. **schemas.py**: Added `REVIEW_PR` and `LAST_REVIEW_PR` constants + validation (lines 393-395)
2. **plan_header.py**: Added three functions (lines 1338-1437):
   - `update_plan_header_review_pr()` - Set review_pr field
   - `extract_plan_header_review_pr()` - Read review_pr field
   - `clear_plan_header_review_pr()` - Archive to last_review_pr and clear

### Why NOT Threaded Through Creation

The `review_pr` field is NOT threaded through `create_plan_issue()` because:

- Plans exist before review PRs are created
- Review is an optional workflow step
- Multiple reviews may occur over time

Instead, `plan-create-review-pr` uses `update_plan_header_review_pr()` to set the field after PR creation.

### Archival Pattern

`clear_plan_header_review_pr()` implements a two-field archival pattern:

```python
# Archive current review_pr to last_review_pr (if not None)
current_review_pr = updated_data.get(REVIEW_PR)
if current_review_pr is not None:
    updated_data[LAST_REVIEW_PR] = current_review_pr

# Clear review_pr
updated_data[REVIEW_PR] = None
```

This pattern:

- Preserves history in `last_review_pr`
- Clears `review_pr` to signal "no active review"
- Enables re-review detection via `last_review_pr`

### When to Use Update-in-Place

Use this pattern when:

- Field is set **after** issue creation
- Field changes over time (not immutable)
- Field represents current state with archival history

Use creation-time threading when:

- Field is known at creation time
- Field is immutable (e.g., `created_from_workflow_run_url`)

## Optional: Additional Files

Depending on usage, you may also need to update:

- **TUI display**: If shown in TUI, update `src/erk/tui/data/types.py`
- **Plan object**: If exposed on Plan domain object, update `src/erk/core/domain/plan.py`
- **erk exec reference**: Update `.claude/skills/erk-exec/reference.md` CLI table

## Verification

After making changes:

1. Run `make fast-ci` to catch type errors
2. Verify field appears correctly in created issues
3. Verify field can be read back via `erk exec get-plan-metadata`

## Related Topics

- [Learn Plan Metadata Preservation](learn-plan-metadata-fields.md) - Critical metadata fields
- [Plan Lifecycle](lifecycle.md) - Overall plan state management

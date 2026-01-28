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

## Concrete Example: review_pr Field

The `review_pr` field was added following this workflow. Here's how each step was implemented:

### 1. schemas.py - Define the Field

```python
# Add to PlanHeaderFieldName
PlanHeaderFieldName = Literal[
    # ... existing fields ...
    "review_pr",
]

# Add constant
REVIEW_PR: Literal["review_pr"] = "review_pr"

# Add validation in validate_plan_header_data()
if REVIEW_PR in data and data[REVIEW_PR] is not None:
    if not isinstance(data[REVIEW_PR], int) or data[REVIEW_PR] <= 0:
        raise ValueError("review_pr must be a positive integer or null")
```

### 2. plan_header.py - Update Functions

Two functions were added (not threading through create):

```python
def update_plan_header_review_pr(issue_body: str, review_pr: int) -> str:
    """Update the review_pr field in an existing plan header."""
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("No plan-header metadata block found")

    updated_data = dict(block.data)
    updated_data[REVIEW_PR] = review_pr
    PlanHeaderSchema().validate(updated_data)

    return replace_metadata_block_in_body(issue_body, "plan-header", updated_data)

def extract_plan_header_review_pr(issue_body: str) -> int | None:
    """Extract the review_pr field from a plan header."""
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        return None
    return block.data.get(REVIEW_PR)
```

### Why Not Thread Through create_plan_header_block()?

Unlike fields set at plan creation time, `review_pr` is populated AFTER the plan issue exists - when the review PR is created. This requires an update-in-place pattern rather than threading through creation functions.

### 3-5. Remaining Steps

For this field, steps 3-5 (plan_issues.py, plan_save_to_issue.py, test fixtures) were NOT needed because:

- Field is set after issue creation, not during
- No CLI option needed (set by exec command)
- Tests use direct header manipulation

## Related Topics

- [Learn Plan Metadata Preservation](learn-plan-metadata-fields.md) - Critical metadata fields
- [Plan Lifecycle](lifecycle.md) - Overall plan state management

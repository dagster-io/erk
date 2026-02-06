---
title: Metadata Field Addition Workflow
read_when:
  - "adding a new field to plan-header metadata"
  - "extending plan issue schema"
  - "coordinating metadata changes across files"
last_audited: "2026-02-05 20:38 PT"
audit_result: edited
---

# Metadata Field Addition Workflow

Adding a new field to the plan-header metadata block requires coordinated changes across multiple files. This checklist ensures nothing is missed.

## 5-File Coordination Checklist

### 1. schemas.py -- Define the Field

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

Three changes required in this file:

- Add the field name as a new entry in the `PlanHeaderFieldName` Literal union type
- Add a module-level constant with a matching `Literal` type (e.g., `YOUR_NEW_FIELD: Literal["your_new_field"] = "your_new_field"`)
- Add validation logic inside `PlanHeaderSchema.validate()` -- follow the existing pattern of checking `if FIELD in data and data[FIELD] is not None:` then validating the type. Also add the constant to the `optional_fields` set in that method.

### 2. plan_header.py -- Thread the Parameter

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`

Two functions need the new parameter added (both use keyword-only args):

- `create_plan_header_block()` -- Add the parameter and conditionally include it in the `data` dict (follow existing pattern: `if field is not None: data[FIELD] = field`). This function returns a `MetadataBlock`, not a string.
- `format_plan_header_body()` -- Add the same parameter and pass it through to `create_plan_header_block()`.

### 3. plan_issues.py -- Thread Through Issue Creation

**File:** `packages/erk-shared/src/erk_shared/gateway/github/plan_issues.py`

Add the parameter to `create_plan_issue()` and pass it through to `format_plan_header_body()`. All parameters after the positional ones are keyword-only. Review the existing call site to see the current parameter threading pattern.

### 4. plan_save_to_issue.py -- Add CLI Option (if CLI-exposed)

**File:** `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`

Only needed if the field should be settable from the CLI. If so:

- Add a `@click.option("--your-new-field", ...)` decorator to the `plan_save_to_issue` function
- Add the corresponding parameter to the function signature
- Pass it through to `create_plan_issue()`

### 5. Test Helpers -- Update format_plan_header_body_for_test

**File:** `tests/test_utils/plan_helpers.py`

Add the parameter to `format_plan_header_body_for_test()` and pass it through to `format_plan_header_body()`. This helper provides defaults so tests only specify the fields they care about. Also update any tests that construct plan headers directly.

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

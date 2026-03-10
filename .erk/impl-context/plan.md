# Plan: Store planning run ID as a proper metadata field

## Context

The current PR (`plnd/show-planning-run-id-03-10-1209`) adds URL-parsing logic in the TUI to extract a GitHub Actions run ID from the `created_from_workflow_run_url` field. This is backwards — the remote planning process already has the run ID available as `github.run_id` in CI, constructs a URL from it, and then the TUI has to parse it back out. Instead, the planning process should store the run ID directly as a first-class metadata field.

## Approach

Add a new `CREATED_FROM_WORKFLOW_RUN_ID` plan header field. Pass `github.run_id` from CI alongside the existing URL. The TUI reads the run ID directly — no parsing.

## Changes

### 1. Schema — `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

- Add `"created_from_workflow_run_id"` to `PlanHeaderFieldName` union
- Add constant: `CREATED_FROM_WORKFLOW_RUN_ID: Literal["created_from_workflow_run_id"] = "created_from_workflow_run_id"` (after `CREATED_FROM_WORKFLOW_RUN_URL`, ~line 398)
- Add to `optional_fields` in `PlanHeaderSchema.validate()`
- Add string-or-null validation (same pattern as `created_from_workflow_run_url`)
- Update docstring

### 2. Plan header functions — `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`

- Import `CREATED_FROM_WORKFLOW_RUN_ID`
- Add `created_from_workflow_run_id: str | None` param to both `create_plan_header_block()` and `format_plan_header_body()`
- Add conditional inclusion: `if created_from_workflow_run_id is not None: data[CREATED_FROM_WORKFLOW_RUN_ID] = created_from_workflow_run_id`

### 3. PlannedPR backend — `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`

- Import `CREATED_FROM_WORKFLOW_RUN_ID`
- In `create_plan()` (~line 317): extract `created_from_workflow_run_id` from metadata dict (same pattern as `created_from_workflow_run_url_raw`)
- Pass through to `format_plan_header_body()` call (~line 344)
- In second `format_plan_header_body()` call (~line 649): pass `created_from_workflow_run_id=None`

### 4. All other `format_plan_header_body()` call sites — pass `created_from_workflow_run_id=None`

- `src/erk/cli/commands/consolidate_learn_plans_dispatch.py:141`
- `src/erk/cli/commands/one_shot_remote_dispatch.py:337`
- `tests/core/test_plan_context_provider.py` (multiple calls)
- `tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py:33`

### 5. CLI command — `src/erk/cli/commands/exec/scripts/plan_save.py`

- Add Click option `--created-from-workflow-run-id`
- Thread through `plan_save()` → `_save_plan_via_planned_pr()` → `_save_as_planned_pr()`
- Add to metadata dict: `if created_from_workflow_run_id is not None: metadata["created_from_workflow_run_id"] = created_from_workflow_run_id`

### 6. CI workflows

- `.github/workflows/one-shot.yml` (~line 155): add `WORKFLOW_RUN_ID: ${{ github.run_id }}`
- `.github/workflows/learn.yml` (~line 67): add `WORKFLOW_RUN_ID: ${{ github.run_id }}`

### 7. Skills/commands

- `.claude/commands/erk/system/one-shot-plan.md` (~line 73): add `--created-from-workflow-run-id "$WORKFLOW_RUN_ID"` to plan-save invocation, add conditional note
- `.claude/commands/erk/learn.md` (~line 715): add parallel conditional block for `WORKFLOW_RUN_ID`

### 8. TUI display — `src/erk/tui/data/real_provider.py`

- Import `CREATED_FROM_WORKFLOW_RUN_ID`
- Replace URL-parsing fallback (lines 664-673) with direct field read:

```python
else:
    created_run_id = header_str(plan.header_fields, CREATED_FROM_WORKFLOW_RUN_ID)
    created_run_url = header_str(plan.header_fields, CREATED_FROM_WORKFLOW_RUN_URL)
    if created_run_id is not None:
        run_id = created_run_id
        run_url = created_run_url
        run_id_display = created_run_id
    elif created_run_url is not None:
        # Backward compat: parse from URL for plans created before this change
        url_parts = created_run_url.rstrip("/").split("/")
        if len(url_parts) >= 1 and url_parts[-1].isdigit():
            run_id = url_parts[-1]
            run_url = created_run_url
            run_id_display = run_id
```

### 9. Test helper — `tests/test_utils/plan_helpers.py`

- Add `created_from_workflow_run_id: str | None = None` param to `format_plan_header_body_for_test()`
- Thread through to `format_plan_header_body()`

### 10. Tests — `tests/tui/data/test_provider.py`

- Update existing tests to use `created_from_workflow_run_id` field
- Keep URL-parsing tests as backward compatibility coverage
- Add test confirming direct field takes precedence over URL parsing

### 11. Reference doc — `.claude/skills/erk-exec/reference.md` (~line 989)

- Add `--created-from-workflow-run-id` row

## Verification

1. Run `make fast-ci` to verify all tests pass (unit + lint + type checks)
2. Check that existing tests in `TestPlanningRunIdFallback` pass with the new approach
3. Verify the schema validates correctly with the new optional field

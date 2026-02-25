# Plan: Objective #7724, Node 5.1+5.2 — Rename issue_number → plan_number in plan CLI commands

Part of Objective #7724, Nodes 5.1 and 5.2.

## Context

This is Phase 5 of a multi-phase mechanical rename of `issue_number` → `plan_number` across plan-related code. Phases 1-4 are complete (PRs #7849, #7896, #7908, #8122, #8134). This phase covers the CLI command layer under `src/erk/cli/commands/pr/` and `src/erk/cli/commands/plan/`.

## Scope

### Source files to modify (Node 5.1)

**Straightforward renames** — all `issue_number` locals/params → `plan_number`:

| File | Occurrences | Notes |
|------|-------------|-------|
| `src/erk/cli/commands/pr/checkout_cmd.py` | ~19 | 3 function params, locals, f-strings. Do NOT rename `parse_issue_number_from_url` (external import from erk_shared) |
| `src/erk/cli/commands/pr/close_cmd.py` | 2 | 1 function param + 1 usage |
| `src/erk/cli/commands/pr/check_cmd.py` | ~15 | `validate_plan_format` param, locals, `expected_issue_number` → `expected_plan_number` |
| `src/erk/cli/commands/pr/view_cmd.py` | 3 | Local variable only |
| `src/erk/cli/commands/pr/log_cmd.py` | ~10 | TypedDict field, function param, locals, metadata string key (see special case below) |
| `src/erk/cli/commands/plan/learn/complete_cmd.py` | 4 | Local variable only |
| `src/erk/cli/commands/plan/docs/extract_cmd.py` | 3 | Local variable only |
| `src/erk/cli/commands/plan/docs/unextract_cmd.py` | 3 | Local variable only |

**Skip — external type not yet renamed:**

| File | Notes |
|------|-------|
| `src/erk/cli/commands/pr/create_cmd.py` | `result.issue_number` accesses `CreatePlanIssueResult` from erk_shared. Do NOT rename — the external type hasn't been renamed yet |
| `src/erk/cli/commands/pr/list_cmd.py` | No `issue_number` occurrences — no changes needed |

### Special case: log_cmd.py metadata reading

`PlanCreatedMetadata` TypedDict field → rename to `plan_number`.

The `_extract_plan_created_event` function reads `"issue_number"` key from stored GitHub metadata blocks (written by `create_plan_block()` in erk_shared, which still uses `issue_number`). Approach:
- Rename TypedDict field: `issue_number: int` → `plan_number: int`
- Keep reading `"issue_number"` from `data` dict (backward compat with stored metadata)
- Store as `metadata["plan_number"]`

### Test files (Node 5.2)

Tests invoke CLI via `CliRunner` with positional arguments and assert on output strings. Internal variable renames should not require test changes. Verify by running the test suite.

Test files to verify:
- `tests/commands/pr/test_checkout_plan.py`
- `tests/commands/pr/test_create.py`
- `tests/commands/pr/test_close.py`
- `tests/commands/pr/test_check_plan.py`
- `tests/commands/pr/test_view.py`
- `tests/commands/pr/test_log.py`
- `tests/commands/plan/learn/test_complete.py`
- `tests/commands/plan/docs/test_docs.py`

Exception: `test_check_plan.py` calls `validate_plan_format()` with positional args, so param name change is transparent.

## Implementation steps

1. **checkout_cmd.py**: Rename `issue_number` → `plan_number` in `_checkout_plan`, `_checkout_plan_pr`, `_display_multiple_prs` params and all local usages. Keep `parse_issue_number_from_url` import unchanged.
2. **close_cmd.py**: Rename param and usage in `_close_linked_prs`.
3. **check_cmd.py**: Rename in `validate_plan_format` param/docstring, `_check_plan_format` locals, `_check_pr_body` locals. Also `expected_issue_number` → `expected_plan_number`.
4. **view_cmd.py**: Rename local variable.
5. **log_cmd.py**: Rename `PlanCreatedMetadata.issue_number` → `plan_number`, update `_extract_plan_created_event` to read `"issue_number"` from data but store as `"plan_number"`, rename param/locals in `_output_timeline`.
6. **learn/complete_cmd.py**: Rename local variable.
7. **docs/extract_cmd.py**: Rename local variable.
8. **docs/unextract_cmd.py**: Rename local variable.
9. **Run tests** via devrun agent to verify no breakage.

## Verification

- Run `make fast-ci` to verify all unit tests pass
- Specifically check: `pytest tests/commands/pr/ tests/commands/plan/ -x`
- Grep for remaining `issue_number` in modified files to confirm completeness (expect zero hits except the `parse_issue_number_from_url` import and `result.issue_number` in create_cmd.py)

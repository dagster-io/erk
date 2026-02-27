# Plan: Delete .impl/issue.json Legacy Support (Objective #7724 Node 9.6)

## Context

Objective #7724 renames `issue_number` → `plan_number` throughout the codebase. During reevaluation, we discovered that several files still contain legacy fallback code that reads from `.impl/issue.json` (the old impl-folder format, superseded by `plan-ref.json`). The user wants to delete this legacy support entirely as a new node in the objective.

`plan-ref.json` is the current format and has been for some time. `issue.json` support is dead weight — removing it clarifies the codebase and completes the rename objective's intent.

## Scope: Files to Change

### Source code (fallback removal)

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/impl_folder.py` | Remove the 3rd fallback in `read_plan_ref()`: the `issue.json` branch (lines ~355-361). Two-level fallback remains: `plan-ref.json` → `ref.json`. |
| `packages/erk-shared/src/erk_shared/gateway/gt/operations/finalize.py` | Change `is_learn_plan()` to read labels from `plan-ref.json` (via `read_plan_ref()`) instead of `issue.json` directly. Remove the `issue.json` file read path. |
| `packages/erk-shared/src/erk_shared/gateway/gt/types.py` | Delete vestigial `issue_number: int | None = None` field (never populated, comment says "linked via .impl/issue.json"). |
| `packages/erk-statusline/src/erk_statusline/statusline.py` | Remove `issue.json` fallback from `_load_impl_data()`. Remove legacy `issue.json` branch from `get_issue_number()` and `get_objective_issue()`. Update stale docstrings on `render_status_line()` and related functions that still say `.impl/issue.json`. |
| `src/erk/cli/commands/wt/list_cmd.py` | Remove `issue.json` fallback in `_get_impl_issue()` (lines ~105-113). |
| `src/erk/cli/commands/exec/scripts/mark_impl_started.py` | Update docstring (references `.erk/impl-context/issue.json`). |
| `src/erk/cli/commands/exec/scripts/mark_impl_ended.py` | Update docstring. |
| `src/erk/cli/commands/exec/scripts/impl_init.py` | Update docstring/comment. |

### Tests (update or delete)

| File | Change |
|------|--------|
| `packages/erk-shared/tests/unit/integrations/gt/operations/test_finalize.py` | Rewrite tests to use `plan-ref.json` format instead of `issue.json`. The logic being tested (learn plan label detection) still exists — just via different source. |
| `packages/erk-statusline/tests/test_statusline.py` | Remove test cases that test `issue.json` fallback behavior (the fallback is being deleted). Keep tests that exercise `plan-ref.json` path. |

## Key Implementation Detail: finalize.py

`is_learn_plan()` currently reads `issue.json` directly to check for `"erk-learn"` label. After this change, it should instead call `read_plan_ref()` (already imported from `impl_folder.py`) and check the `labels` field on the returned `PlanRef`. `plan-ref.json` already carries a `labels` array — no new data needed.

## Verification

After implementation, run:
```
pytest packages/erk-shared/tests/unit/integrations/gt/operations/test_finalize.py packages/erk-statusline/tests/ -v
```

And confirm:
- `grep -r "issue\.json" packages/ src/ --include="*.py" | grep -v __pycache__ | grep -v "\.pyc"` returns only the migration compat readers in `metadata_blocks.py` (intentional) and nothing else.

## Steps

1. Remove `issue.json` fallback from `impl_folder.py`
2. Update `finalize.py` to use `read_plan_ref()` instead of `issue.json` direct read
3. Delete vestigial `issue_number` field from `gt/types.py`
4. Remove `issue.json` fallback from `statusline.py`, update docstrings
5. Remove `issue.json` fallback from `wt/list_cmd.py`
6. Update docstrings in exec scripts (`mark_impl_started.py`, `mark_impl_ended.py`, `impl_init.py`)
7. Rewrite `test_finalize.py` tests to use `plan-ref.json` format
8. Update `test_statusline.py` to remove `issue.json` fallback test cases
9. Run tests and verify grep clean

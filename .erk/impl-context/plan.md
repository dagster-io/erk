# Plan: Smoke test through production `dispatch_one_shot` code path

## Context

The `erk doctor workflow --smoke-test` command manually creates a branch, PR, and dispatches the one-shot workflow — duplicating logic from `dispatch_one_shot()`. The PR it creates lacks the `plan-header` metadata block that the CI workflow expects, causing the "Update lifecycle stage to planning" step to fail with `no_plan_header`.

The fix: rewrite `run_smoke_test()` to delegate to `dispatch_one_shot()`, the production code path that already creates proper plan-header metadata, footer, labels, and dispatch metadata.

## Changes

### 1. Rewrite `src/erk/core/workflow_smoke_test.py`

- **Remove** the manual branch/PR/workflow creation from `run_smoke_test()`
- **Replace** with a call to `dispatch_one_shot()` from `erk.cli.commands.one_shot_dispatch`
- Pass `slug="smoke-test"` in `OneShotDispatchParams` to skip LLM slug generation
- Branch names will change from `smoke-test/{timestamp}` to `plnd/smoke-test-{timestamp}` (production pattern)
- Map `OneShotDispatchResult` back to `SmokeTestResult` (keeping the existing return type for the CLI layer)
- Wrap `dispatch_one_shot()` call in try/except to convert exceptions to `SmokeTestError`
- Compute `run_url` from the result (dispatch_one_shot doesn't return it)

Key details:
- `OneShotDispatchParams(prompt=SMOKE_TEST_PROMPT, model=None, extra_workflow_inputs={}, slug="smoke-test")`
- `dispatch_one_shot(ctx, params=params, dry_run=False)`
- `dispatch_one_shot` already handles: create_branch, commit, push, create_pr with plan-header, add footer, add labels (`erk-pr`, `erk-plan`), trigger workflow, write dispatch metadata, post queued comment

- **Update** `cleanup_smoke_tests()` to find branches matching `plnd/smoke-test-` instead of `smoke-test/`
- Update `SMOKE_TEST_BRANCH_PREFIX` constant to `"plnd/smoke-test-"`

### 2. Update `src/erk/cli/commands/doctor_workflow.py`

- `_handle_smoke_test` already calls `run_smoke_test(ctx)` and handles the result — this interface stays the same since `run_smoke_test` still returns `SmokeTestResult | SmokeTestError`
- No changes needed here (the abstraction in `workflow_smoke_test.py` shields the CLI)

### 3. Update `tests/unit/core/test_workflow_smoke_test.py`

- Update `test_creates_branch_pr_and_triggers_workflow`: the test context needs to support `dispatch_one_shot`'s dependencies (plan_backend, issues, local_config are already provided by `ErkContext.for_test()` defaults)
- Branch assertion changes from `startswith("smoke-test/")` to `startswith("plnd/smoke-test-")`
- Label assertions: expect both `erk-pr` and `erk-plan` labels (production adds both, current test only expects `erk-plan`)
- PR body should contain plan-header metadata block
- Also needs `get_current_branch` to return something (dispatch_one_shot checks for detached HEAD)
- Update cleanup tests: branch names change from `smoke-test/01-15-1430` to `plnd/smoke-test-01-15-1430`

### 4. Update `tests/commands/doctor/test_doctor_workflow.py`

- No changes expected — the CLI tests don't exercise `--smoke-test` (only static checks, --wait validation, --cleanup)

## Files to modify

1. `src/erk/core/workflow_smoke_test.py` — main rewrite
2. `tests/unit/core/test_workflow_smoke_test.py` — test updates
3. `tests/commands/doctor/test_doctor_workflow.py` — verify no changes needed

## Verification

1. Run unit tests: `uv run pytest tests/unit/core/test_workflow_smoke_test.py`
2. Run CLI tests: `uv run pytest tests/commands/doctor/test_doctor_workflow.py`
3. Run ty/ruff checks on modified files

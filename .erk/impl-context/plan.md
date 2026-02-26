# Plan: Update tests for renamed pr/* files (Objective #7724, Node 6.2)

Part of Objective #7724 — Rename issue_number to plan_number in plan-related code

## Context

Phases 5 (PR #8139) and 6.1 (PR #8266) renamed `issue_number` → `plan_number` in pr/* source files but did not fully update corresponding test files. Node 6.2 catches up all test updates for pr/* files.

**Key finding:** Most `issue_number` references remaining in pr/* test files are calls to **erk-shared APIs** (`create_plan_block(issue_number=...)`, `create_submission_queued_block(issue_number=...)`) or **JSON fixtures** matching the `.impl/issue.json` schema — both unchanged until Phase 9. These are **out of scope** for this node.

## Changes

### 1. Fix missed source error message in close_cmd.py

**File:** `src/erk/cli/commands/pr/close_cmd.py`

- Line 58: `f"Issue #{number} not found"` → `f"Plan #{number} not found"`
- Line 41: Docstring `"Close a plan by issue number or GitHub URL"` → `"Close a plan by plan number or GitHub URL"`
- Line 52: Comment `# Parse issue number` → `# Parse plan number`

### 2. Update test_close.py to match

**File:** `tests/commands/pr/test_close.py`

- Line 24: Rename function `test_close_plan_with_issue_number` → `test_close_plan_with_plan_number`
- Line 25: Update docstring `"Test closing a plan with issue number"` → `"Test closing a plan with plan number"`
- Line 71: `assert "Issue #999 not found"` → `assert "Plan #999 not found"`

### 3. No changes needed (already clean)

These test files have no `issue_number` references — no work needed:
- `tests/commands/pr/test_dispatch.py` (updated in PR #8266)
- `tests/unit/cli/commands/pr/test_metadata_helpers.py`
- `tests/commands/pr/test_create.py`
- `tests/commands/pr/test_rewrite.py`
- `tests/commands/pr/test_submit.py`
- `tests/commands/pr/test_submit_graphite_disabled.py`
- `tests/commands/pr/test_submit_pr_cache_polling.py`

### 4. Deferred to Phase 9 (blocked by erk-shared)

These `issue_number` references call erk-shared APIs with not-yet-renamed parameters:
- `tests/commands/pr/test_log.py` — 8 calls to `create_plan_block(issue_number=...)`, `create_submission_queued_block(issue_number=...)`, `create_workflow_started_block(issue_number=...)`
- `tests/commands/pr/test_list.py` — 3 JSON fixtures with `"issue_number"` matching `.impl/issue.json` schema
- `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py` — 1 JSON fixture
- `tests/unit/cli/commands/pr/submit_pipeline/test_prepare_state.py` — 2 JSON fixtures

## Verification

1. Run `pytest tests/commands/pr/test_close.py` — all tests pass with updated assertions
2. Run `pytest tests/commands/pr/` — no regressions in other pr/* tests
3. Run `pytest tests/unit/cli/commands/pr/` — no regressions in unit pr/* tests
4. Run `ruff check` and `ty check` on modified files

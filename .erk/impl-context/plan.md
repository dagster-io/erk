# Plan: Update tests for renamed core modules (Objective #7724, Node 7.2)

## Context

Part of **Objective #7724** — Rename `issue_number` to `plan_number` in plan-related code.

Node 7.1 (plan in progress, #8349) renames `issue_number` → `plan_number` in the source files: `output_filter.py`, `prompt_executor.py`, `codex_output_parser.py`, and `cli/output.py`. Node 7.2 updates the corresponding tests to match those source renames.

**Dependency:** This plan should be implemented after plan #8349 (nodes 6.2 + 7.1) lands, since the test changes must align with the source renames.

## Critical Boundary: erk_shared types

`CommandResult.issue_number` and `IssueNumberEvent` are defined in `erk_shared` (Phase 9). These must NOT be renamed in this phase:

- **DO rename:** Local dict keys (`"issue_number"` → `"plan_number"`), local variables, test method names
- **DO NOT rename:** `CommandResult(issue_number=...)` constructor kwargs, `.issue_number` attribute access, `IssueNumberEvent` class references

## Files to Modify

### 1. `tests/core/test_output_filter.py` (6 occurrences)

Rename dict keys in assertions from `"issue_number"` to `"plan_number"`:
- Lines 37, 45, 57, 65, 84, 92: `"issue_number"` → `"plan_number"` in `extract_pr_metadata` return value assertions

### 2. `tests/core/test_prompt_executor.py` (16 occurrences)

Rename dict keys in test data and assertions:
- Lines 25, 64: `"issue_number"` in test input JSON data → `"plan_number"`
- Lines 41, 87, 234, 256, 388, 395, 402, 409, 416, 443, 462, 484, 494, 503: `result["issue_number"]` → `result["plan_number"]`

### 3. `tests/unit/core/test_codex_output_parser.py` (1 occurrence)

Rename test method:
- Line 187: `test_extracts_issue_number_from_text` → `test_extracts_plan_number_from_text`

### 4. `tests/core/test_cli_output.py` — NO CHANGES

All 4 occurrences are `CommandResult(issue_number=None)` constructor kwargs — these cross the erk_shared boundary and stay unchanged until Phase 9.

### 5. `tests/unit/fakes/test_fake_prompt_executor.py` — NO CHANGES

Confirmed 0 occurrences of `issue_number` (grep verified).

## Implementation Steps

1. After plan #8349 lands, update `tests/core/test_output_filter.py`: replace all 6 `"issue_number"` dict keys with `"plan_number"` using `replace_all`
2. Update `tests/core/test_prompt_executor.py`: replace `"issue_number"` dict keys and `result["issue_number"]` with `"plan_number"` equivalents (16 occurrences)
3. Update `tests/unit/core/test_codex_output_parser.py`: rename test method from `test_extracts_issue_number_from_text` to `test_extracts_plan_number_from_text`
4. Run scoped tests: `pytest tests/core/test_output_filter.py tests/core/test_prompt_executor.py tests/unit/core/test_codex_output_parser.py tests/core/test_cli_output.py`
5. Run `ruff check` and `ty check` on modified files
6. Run `make fast-ci` for full validation

## Verification

- All modified test files pass individually
- `make fast-ci` passes (lint, format, type checks, unit tests)
- No remaining `"issue_number"` dict keys in the modified test files (boundary kwargs in test_cli_output.py are expected)

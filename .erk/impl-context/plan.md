# Plan: Update tests for renamed core modules (Objective #7724, Node 7.2)

Part of Objective #7724 (Rename issue_number to plan_number), Node 7.2.

## Context

Node 7.1 (PR #8349) renames `issue_number` → `plan_number` in local variables, dict keys, and docstrings across four core source files:
- `src/erk/core/output_filter.py` — dict keys `"issue_number"` → `"plan_number"` in return values
- `src/erk/core/prompt_executor.py` — local vars and dict keys
- `src/erk/core/codex_output_parser.py` — local vars
- `src/erk/cli/output.py` — local vars and user-facing text (`"📋 Linked Issue"` → `"📋 Linked Plan"`)

Node 7.2 updates the **test files** to match those source changes. The `erk_shared` boundary is NOT changing in this node — `IssueNumberEvent`, `CommandResult.issue_number`, and the `issue_number=` keyword argument to `CommandResult()` all remain unchanged (those rename in Phase 9).

**Dependency:** This plan MUST be implemented after node 7.1 (PR #8349) lands. The test changes reference the new dict keys (`"plan_number"`) that only exist after 7.1 is merged.

## Changes

### 1. `tests/core/test_output_filter.py` — 6 occurrences

All dict key references `"issue_number"` → `"plan_number"` in test data and assertions:

- **Line 37**: `"issue_number": 456,` → `"plan_number": 456,`
- **Line 45**: `"issue_number": 456,` → `"plan_number": 456,`
- **Line 57**: `"issue_number": None,` → `"plan_number": None,`
- **Line 65**: `"issue_number": None` → `"plan_number": None` (in inline dict assertion)
- **Line 84**: `"issue_number": None,` → `"plan_number": None,`
- **Line 92**: `"issue_number": None` → `"plan_number": None` (in inline dict assertion)

These are all dict key assertions matching the return value of `extract_pr_metadata()`, which after 7.1 returns `"plan_number"` instead of `"issue_number"`.

### 2. `tests/core/test_prompt_executor.py` — 16 occurrences

All dict key references `"issue_number"` → `"plan_number"` in test data and assertions:

- **Line 25**: `"issue_number": 456,` → `"plan_number": 456,` (JSON test data string)
- **Line 41**: `result["issue_number"] == 456` → `result["plan_number"] == 456`
- **Line 64**: `"issue_number": 101,` → `"plan_number": 101,` (JSON test data string)
- **Line 87**: `result["issue_number"] == 101` → `result["plan_number"] == 101`
- **Line 234**: `result["issue_number"] == 1308` → `result["plan_number"] == 1308`
- **Line 256**: `result["issue_number"] is None` → `result["plan_number"] is None`
- **Line 388**: `result["issue_number"] == 456` → `result["plan_number"] == 456`
- **Line 395**: `result["issue_number"] == 456` → `result["plan_number"] == 456`
- **Line 402**: `result["issue_number"] is None` → `result["plan_number"] is None`
- **Line 409**: `result["issue_number"] == 100` → `result["plan_number"] == 100`
- **Line 416**: `result["issue_number"] == 1308` → `result["plan_number"] == 1308`
- **Line 443**: `result["issue_number"] == 1308` → `result["plan_number"] == 1308`
- **Line 462**: `result["issue_number"] == 1308` → `result["plan_number"] == 1308`
- **Line 484**: `result["issue_number"] is None` → `result["plan_number"] is None`
- **Line 494**: `result["issue_number"] is None` → `result["plan_number"] is None`
- **Line 503**: `result["issue_number"] is None` → `result["plan_number"] is None`

Additionally, the section comment on **line 380** should be updated:
- `# Issue number extraction patterns` → `# Plan number extraction patterns`

### 3. `tests/unit/core/test_codex_output_parser.py` — 1 occurrence

Rename the test method:

- **Line 187**: `def test_extracts_issue_number_from_text(self)` → `def test_extracts_plan_number_from_text(self)`

Note: The test body itself doesn't need changes — it asserts on `IssueNumberEvent` which is an `erk_shared` type that doesn't change until Phase 9.

### 4. `tests/core/test_cli_output.py` — 0 changes needed

This file uses `CommandResult(issue_number=None, ...)` which is the `erk_shared` constructor keyword. Since `CommandResult.issue_number` field stays unchanged until Phase 9, **no changes are needed in this file**.

The user-facing text change (`"📋 Linked Issue"` → `"📋 Linked Plan"`) in `cli/output.py` is a source change (7.1), not a test change. The existing tests in `test_cli_output.py` don't assert on that specific text string, so they'll pass without modification.

### 5. `tests/fakes/prompt_executor.py` — 0 changes needed

The `FakePromptExecutor` uses `simulated_issue_number`, `IssueNumberEvent`, and `CommandResult(issue_number=...)` — all of which are `erk_shared` boundary types that don't change until Phase 9. **No changes needed.**

## Files NOT Changing

- `tests/core/test_cli_output.py` — uses `CommandResult.issue_number` (erk_shared boundary)
- `tests/fakes/prompt_executor.py` — uses `IssueNumberEvent` and `CommandResult(issue_number=...)` (erk_shared boundary)
- Any test files in `tests/unit/cli/commands/exec/scripts/` — those test exec scripts, not core modules
- Any `erk_shared` test files — those are Phase 9

## Implementation Details

### Pattern to follow

Use `replace_all` for bulk substitution where possible:

1. In `test_output_filter.py`: Replace `"issue_number"` with `"plan_number"` (all 6 are dict keys)
2. In `test_prompt_executor.py`: Replace `"issue_number"` with `"plan_number"` (all 16 are dict keys/assertions), then update the section comment
3. In `test_codex_output_parser.py`: Rename the single test method

### erk_shared boundary reminder

Do NOT rename:
- `IssueNumberEvent` class references
- `CommandResult(issue_number=...)` constructor keywords
- `result.issue_number` attribute access

These are all `erk_shared` types that stay unchanged until Phase 9.

## Execution Order

1. Update `tests/core/test_output_filter.py`
2. Update `tests/core/test_prompt_executor.py`
3. Update `tests/unit/core/test_codex_output_parser.py`
4. Run tests to verify

## Verification

1. Run the specific test files:
   - `pytest tests/core/test_output_filter.py`
   - `pytest tests/core/test_prompt_executor.py`
   - `pytest tests/unit/core/test_codex_output_parser.py`
2. Run `make fast-ci` — all unit tests pass
3. Grep to confirm no stale `"issue_number"` dict keys remain in the 3 modified test files
4. Grep to confirm `IssueNumberEvent` references are still present (erk_shared boundary preserved)
# Plan: Rename issue_number to plan_number in core modules (Objective #7724, Phase 7)

Part of Objective #7724, Nodes 7.1 + 7.2

## Context

Objective #7724 systematically renames `issue_number` → `plan_number` in plan-related code. Phases 1-6 completed renames in exec scripts, plan_* scripts, impl_* scripts, and pr/* CLI commands. Phase 7 targets the core output/parsing modules and their tests.

**Key boundary:** `CommandResult.issue_number` field and `IssueNumberEvent` class are defined in `erk_shared` (Phase 9) — attribute access (`.issue_number`) and constructor keywords (`issue_number=`) must stay unchanged. Only local variables, internal dict keys, and docstrings change.

## Scope

**github_parsing.py is OUT OF SCOPE** — it contains generic GitHub issue URL parsing (not plan-specific). The objective roadmap says "plan-related parts only" and there are none.

## Changes

### 1. `src/erk/core/output_filter.py` (11 occurrences)

Rename dict keys and local variables in `extract_pr_metadata()` and `extract_pr_metadata_from_text()`:

- Dict key `"issue_number"` → `"plan_number"` in all return dicts (lines 195, 205, 208, 219, 249)
- Local var `issue_number` → `plan_number` (line 213)
- Dict assignment `result["issue_number"]` → `result["plan_number"]` (line 292)
- Docstrings: update references to `issue_number` (lines 186, 190, 192, 236)

### 2. `src/erk/core/prompt_executor.py` (9 occurrences)

Rename local variables and dict keys. Keep `IssueNumberEvent` class name and `extract_pr_metadata`/`extract_pr_metadata_from_text` import names.

- Local var `text_issue_number` → `text_plan_number` (lines 243-245)
- Local var `issue_number_value` → `plan_number_value` (lines 273-275)
- Docstring: `issue_number` → `plan_number` (line 351)
- Dict key `"issue_number"` → `"plan_number"` (line 384)
- Dict access `result["issue_number"] = pr_metadata.get("issue_number")` → `result["plan_number"] = pr_metadata.get("plan_number")` (line 448)

### 3. `src/erk/core/codex_output_parser.py` (3 occurrences)

- Local var `issue_number` → `plan_number` (lines 206-208)
- Keep `IssueNumberEvent` class name (erk_shared boundary)

### 4. `src/erk/cli/output.py` (8 occurrences)

Rename local variables and user-facing text. **Keep** `result.issue_number` attribute access and `CommandResult(issue_number=...)` keyword (erk_shared boundary).

- Local var `issue_number: int | None = None` → `plan_number` (lines 75, 178)
- Assignment `issue_number = result.issue_number` → `plan_number = result.issue_number` (line 81)
- Conditional `if issue_number:` → `if plan_number:` (line 102)
- User-facing text `"📋 Linked Issue: #{issue_number}"` → `"📋 Linked Plan: #{plan_number}"` (line 105)
- Assignment `issue_number = num` → `plan_number = num` (line 223)
- Constructor arg `issue_number=issue_number` → `issue_number=plan_number` (line 259 — keyword stays, value changes)

### 5. `tests/core/test_output_filter.py` (6 occurrences)

- All dict keys `"issue_number"` → `"plan_number"` in test data and assertions (lines 37, 45, 57, 65, 84, 92)

### 6. `tests/core/test_prompt_executor.py` (16 occurrences)

- All dict keys `result["issue_number"]` → `result["plan_number"]` in assertions (lines 25, 41, 64, 87, 234, 256, 388, 395, 402, 409, 416, 443, 462, 484, 494, 503)

### 7. `tests/unit/core/test_codex_output_parser.py` (1 occurrence)

- Test method name `test_extracts_issue_number_from_text` → `test_extracts_plan_number_from_text` (line 187)

## Execution Order

1. Rename in `output_filter.py` (dict keys change here first — upstream)
2. Rename in `prompt_executor.py` (consumes output_filter dicts)
3. Rename in `codex_output_parser.py` (consumes output_filter dicts)
4. Rename in `cli/output.py` (consumes CommandResult, careful with erk_shared boundary)
5. Update all 3 test files
6. Run tests to verify

## Verification

1. `make fast-ci` — all unit tests pass
2. `ruff check` + `ty check` — no lint/type errors
3. Grep to confirm no stale `"issue_number"` dict keys remain in the 4 source files (expect zero matches for `"issue_number"` in output_filter.py, prompt_executor.py, codex_output_parser.py; expect only erk_shared boundary references in output.py)

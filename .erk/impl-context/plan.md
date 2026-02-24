# Plan: Standalone Duplicate Plan Check Command

## Context

PR #8015 added duplicate plan detection via LLM inference, integrated directly into `erk plan create` and `erk exec plan-save-to-issue`. User feedback requests a different approach: **start with a standalone command** rather than hooking into existing workflows. This lets us validate the duplicate detection UX independently before integrating it into automated flows.

Additionally, PR review feedback identified style violations to fix.

## Changes

### 1. Create standalone command: `erk plan duplicate-check`

**New file**: `src/erk/cli/commands/plan/duplicate_check_cmd.py`

Command that takes plan content and checks for duplicates among open plans.

```
erk plan duplicate-check --file plan.md
cat plan.md | erk plan duplicate-check
```

**Interface:**
- `--file PATH` — read plan from file
- Stdin — pipe plan content (fallback if no `--file`)
- Output: styled list of duplicate matches (or "no duplicates found")
- Exit code 0 = no duplicates, exit code 1 = duplicates found (useful for scripting)

**Implementation** — follows `check_cmd.py` pattern:
- Uses `@click.pass_obj` with `ErkContext`
- Reads plan content from file or stdin (reuse pattern from `create_cmd.py` lines 54-71)
- Fetches open `erk-plan` issues, filters out `erk-learn`
- Calls `PlanDuplicateChecker.check()`
- Displays results with styled output

### 2. Register the command

**Edit**: `src/erk/cli/commands/plan/__init__.py`
- Import and add `plan_group.add_command(duplicate_check_plan, name="duplicate-check")`

### 3. Remove workflow integrations (revert to standalone-only)

**Edit**: `src/erk/cli/commands/plan/create_cmd.py`
- Remove `--force` flag
- Remove `_run_duplicate_check()` function
- Remove `PlanDuplicateChecker` import

**Edit**: `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`
- Remove `--skip-duplicate-check` flag
- Remove `_run_non_interactive_duplicate_check()` function
- Remove `PlanDuplicateChecker` and `require_prompt_executor` imports

### 4. Address PR review feedback

**Edit**: `tests/core/test_plan_duplicate_checker.py:15`
- Remove default value from `labels` parameter: `labels: list[str] | None = None` → `labels: list[str] | None` and pass explicitly at call sites

### 5. Write tests for the new command

**New file**: `tests/commands/plan/test_duplicate_check.py`

Tests using `CliRunner` + `ErkContext.for_test()`:
- No duplicates found → exit 0, appropriate output
- Duplicates found → exit 1, displays match info
- No file/stdin → error message
- Empty existing plans → quick no-duplicate result
- LLM error → graceful degradation (proceed, no crash)

## Files Modified

| File | Action |
|------|--------|
| `src/erk/cli/commands/plan/duplicate_check_cmd.py` | **New** — standalone command |
| `src/erk/cli/commands/plan/__init__.py` | Edit — register new command |
| `src/erk/cli/commands/plan/create_cmd.py` | Edit — remove duplicate check integration |
| `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` | Edit — remove duplicate check integration |
| `tests/core/test_plan_duplicate_checker.py` | Edit — fix default parameter |
| `tests/commands/plan/test_duplicate_check.py` | **New** — command tests |
| `src/erk/core/plan_duplicate_checker.py` | No change — core logic stays as-is |

## Existing code to reuse

- `PlanDuplicateChecker` from `src/erk/core/plan_duplicate_checker.py` — all core logic
- Input reading pattern from `create_cmd.py` lines 54-71 (file vs stdin)
- Styled output pattern from `check_cmd.py` lines 157-159
- `ErkContext` context injection pattern

## Verification

1. Run `uv run pytest tests/core/test_plan_duplicate_checker.py` — existing core tests still pass
2. Run `uv run pytest tests/commands/plan/test_duplicate_check.py` — new command tests pass
3. Run `uv run pytest tests/commands/plan/` — no regressions in plan commands
4. Run `uv run ruff check` and `uv run ty check` — no lint/type errors

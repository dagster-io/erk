# Plan: Fix duplicate-check parsing bug and add progress reporting

## Context

`erk plan duplicate-check --plan 7991` fails with:
```
Malformed LLM response: ```json
{"duplicates": []}
```
```

The LLM returns valid JSON wrapped in code fences **followed by extra explanation text**. The code fence stripping logic naively removes the first and last lines, but when there's trailing text after the closing ` ``` `, the last line is the explanation text (not the fence), leaving the closing fence and extra text mixed into the "JSON".

Additionally, the command gives almost no progress feedback — just "Checking against N open plan(s)..." then silence until result or error.

## Changes

### 1. Fix code fence stripping in `_parse_response()`

**File:** `src/erk/core/plan_duplicate_checker.py` (lines 150-155)

**Bug:** Current code does `fence_lines[1:-1]` which assumes the last line is the closing fence. When the LLM appends explanation text after the closing fence, the closing fence ends up *inside* the extracted content, causing JSON parse failure.

**Fix:** Find the actual closing ` ``` ` marker and extract only content between the opening and closing fences:

```python
if stripped.startswith("```"):
    fence_lines = stripped.splitlines()
    # Find the closing fence (first line after opening that is exactly ```)
    close_idx = None
    for i in range(1, len(fence_lines)):
        if fence_lines[i].strip() == "```":
            close_idx = i
            break
    if close_idx is not None:
        stripped = "\n".join(fence_lines[1:close_idx]).strip()
    else:
        # No closing fence, remove just the opening line
        stripped = "\n".join(fence_lines[1:]).strip()
```

### 2. Add progress reporting in `duplicate_check_cmd.py`

**File:** `src/erk/cli/commands/plan/duplicate_check_cmd.py`

After filtering plans and before the LLM call, list the plans being compared:

```
Checking against 7 open plan(s):
  #7991: Add dark mode support
  #7997: Refactor PR pipeline
  #8003: Add Slack integration
  ...

Analyzing for semantic duplicates...
```

This replaces the current single-line "Checking against N open plan(s)..." message. The plan listing shows the user exactly what's being compared, and the "Analyzing..." line indicates the LLM call is in progress.

### 3. Improve error output for debugging

When there's a parse error, include more of the raw response so the user can see what went wrong. Change the error truncation from 200 to 500 chars in `_parse_response()`, and in the CLI command, show the raw response on a separate indented line for readability.

## Files to modify

1. `src/erk/core/plan_duplicate_checker.py` — fix fence stripping, increase error truncation
2. `src/erk/cli/commands/plan/duplicate_check_cmd.py` — add plan listing and progress messages
3. `tests/core/test_plan_duplicate_checker.py` — add test for trailing text after code fence
4. `tests/commands/plan/test_duplicate_check.py` — update expected output for new progress messages

## Verification

1. Run `uv run pytest tests/core/test_plan_duplicate_checker.py` — all tests pass
2. Run `uv run pytest tests/commands/plan/test_duplicate_check.py` — all tests pass
3. Manual: `erk plan duplicate-check --plan <id>` shows plan listing, progress, and correct result

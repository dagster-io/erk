# Replace brittle fence-stripping with raw_decode JSON extraction

## Context

`erk plan duplicate-check` and the relevance checker both ask Haiku to return JSON via `claude --print --output-format text`. Haiku sometimes wraps its JSON in markdown fences with trailing commentary, which breaks the current parser (`fence_lines[1:-1]` assumes the last line is the closing fence).

The fix: use `json.JSONDecoder.raw_decode()` to extract the first JSON object from arbitrary surrounding text, handling all LLM output variations without string manipulation.

## Changes

### 1. Create `src/erk/core/llm_json.py`

New module with `extract_json_dict(text: str) -> dict | None` that:
- Finds first `{` in text
- Uses `json.JSONDecoder.raw_decode()` to parse from that position
- Returns `None` for empty text, no `{` found, parse errors, or non-dict results

### 2. Edit `src/erk/core/plan_duplicate_checker.py`

- Import `extract_json_dict` from `erk.core.llm_json`
- In `_parse_response`: replace fence-stripping block + `_safe_json_parse(stripped)` with `extract_json_dict(output)`
- Delete `_safe_json_parse` function
- Remove `import json` (no longer needed)

### 3. Edit `src/erk/core/plan_relevance_checker.py`

- Same changes as step 2: import `extract_json_dict`, replace fence-stripping + `_safe_json_parse`, delete `_safe_json_parse`, remove `import json`

### 4. Create `tests/core/test_llm_json.py`

Tests for `extract_json_dict`:
- Raw JSON dict -> parsed dict
- Code fence wrapped -> parsed dict
- Trailing text after fence -> parsed dict
- Preamble text before JSON -> parsed dict
- Not JSON -> None
- Empty string -> None
- JSON array (not dict) -> None

### 5. Add trailing-text test to `tests/core/test_plan_duplicate_checker.py`

Add `test_json_wrapped_in_code_fence_with_trailing_text` — the scenario that exposed the original bug.

## Files

| File | Action |
|------|--------|
| `src/erk/core/llm_json.py` | Create |
| `tests/core/test_llm_json.py` | Create |
| `src/erk/core/plan_duplicate_checker.py` | Edit — use `extract_json_dict`, remove fence-stripping + `_safe_json_parse` |
| `src/erk/core/plan_relevance_checker.py` | Edit — same |
| `tests/core/test_plan_duplicate_checker.py` | Edit — add trailing-text test |

## Verification

1. `pytest tests/core/test_llm_json.py` — new utility tests pass
2. `pytest tests/core/test_plan_duplicate_checker.py` — all pass including new trailing-text test
3. `pytest tests/core/test_plan_relevance_checker.py` — all pass
4. `pytest tests/commands/plan/test_duplicate_check.py` — all pass
5. `ruff check` and `ty check` on changed files

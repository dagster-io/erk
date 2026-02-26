# Plan: Add `batch-close-issues-with-comment` exec command

## Context

When consolidating multiple plan issues (e.g., closing 19 issues with the same consolidation comment), the current `close-issue-with-comment` command must be invoked once per issue. This means 19 sequential subprocess invocations, each re-initializing the GitHub gateway. A batch variant amortizes startup cost and provides aggregate reporting.

## Approach

Create a new `batch-close-issues-with-comment` exec command following the canonical batch pattern established by `resolve-review-threads`. The existing single command remains unchanged for interactive/scripting use.

## Files to Create

### 1. `src/erk/cli/commands/exec/scripts/batch_close_issues_with_comment.py`

New batch command following the five-step contract from `docs/learned/cli/batch-exec-commands.md`:

- **Input**: JSON array from stdin, each item: `{"plan_number": int, "comment": str}`
- **TypedDict** for input: `CloseIssueItem` with `plan_number` (int) and `comment` (str)
- **Frozen dataclasses** for output: `BatchCloseResult` and `BatchCloseError`
- **Validation**: `_validate_batch_input()` — validates all items upfront before processing any
  - Checks array type, item is dict, `plan_number` is int, `comment` is str
- **Processing**: Iterate validated items, call `backend.add_comment()` then `backend.close_plan()` per item, collect per-item results
- **Output**: JSON with AND-semantics success flag and per-item results
- **Exit code**: Always 0 (errors encoded in JSON), except context init failures (exit 1)
- **Dependencies**: `require_plan_backend(ctx)`, `require_repo_root(ctx)` — same as single command

Per-item result shape:
```json
{"plan_number": 42, "success": true, "comment_id": "1000000"}
{"plan_number": 999, "success": false, "error": "Failed to add comment to plan #999: ..."}
```

Usage:
```bash
echo '[{"plan_number": 42, "comment": "Consolidated into #100"}]' | erk exec batch-close-issues-with-comment
```

### 2. `tests/unit/cli/commands/exec/scripts/test_batch_close_issues_with_comment.py`

Tests mirroring the single-command tests plus batch-specific scenarios:

- All items succeed (multiple issues closed)
- Partial failure (one issue not found, others succeed)
- Validation failure: not an array
- Validation failure: missing `plan_number` field
- Validation failure: missing `comment` field
- Validation failure: wrong types
- Empty array (succeeds with empty results)
- Invalid JSON stdin

Uses same test infrastructure: `FakeGitHub`, `FakeGitHubIssues`, `PlannedPRBackend`, `ErkContext.for_test()`, `CliRunner` with `input=` for stdin.

## Files to Modify

### 3. `src/erk/cli/commands/exec/group.py`

- Add import for `batch_close_issues_with_comment`
- Add `exec_group.add_command(batch_close_issues_with_comment, name="batch-close-issues-with-comment")`

## Key patterns to reuse

- `resolve_review_threads.py` — canonical batch command structure (line-for-line reference)
- `close_issue_with_comment.py` — per-item processing logic (add_comment + close_plan)
- `docs/learned/cli/batch-exec-commands.md` — five-step contract, two response shapes, AND semantics

## Verification

1. Run unit tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_batch_close_issues_with_comment.py`
2. Run type checker on new file: `uv run ty check src/erk/cli/commands/exec/scripts/batch_close_issues_with_comment.py`
3. Run linter: `uv run ruff check src/erk/cli/commands/exec/scripts/batch_close_issues_with_comment.py`

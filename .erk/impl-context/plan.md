# Plan: `erk exec debug-impl-run` — Implementation Run Debugger

## Context

Debugging a failed `plan-implement` workflow run currently requires ~10 round-trips of bash commands with inline Python to extract basic facts from GitHub Actions logs. The core problems:

1. **`gh run view --log` truncates** — only returns ~58 lines per step, missing most of the Claude session
2. **Stream-JSON is embedded in GH Actions log lines** — requires stripping timestamps, parsing JSONL, then interpreting the Claude message structure
3. **No existing tool covers this** — `/local:debug-ci` handles lint/test failures, not implementation session failures

The REST API (`/repos/{owner}/{repo}/actions/jobs/{job_id}/logs`) returns **full** untruncated logs. The `ci_generate_summaries.py` script already demonstrates this pattern.

**Goal:** Replace the 10-round-trip manual debugging with a single `erk exec debug-impl-run <run_id>` command that outputs a structured summary.

## Files to Create

### 1. `src/erk/core/impl_run_parser.py` — Pure parsing module

No I/O, no subprocess calls — just string parsing and frozen dataclasses.

**Types:**
```python
@dataclass(frozen=True)
class ToolAction:
    tool_name: str
    summary: str       # e.g. "Read src/erk/foo.py", "Bash: uv run pytest"

@dataclass(frozen=True)
class ImplRunSummary:
    session_id: str | None
    model: str | None
    duration_ms: int | None
    num_turns: int | None
    is_error: bool | None
    exit_code: int | None
    cost_usd: float | None
    tool_actions: list[ToolAction]
    error_messages: list[str]
    files_read: list[str]
    files_modified: list[str]
    assistant_messages: list[str]  # Truncated to ~200 chars each
```

**Functions:**
- `extract_stream_json_lines(job_log: str) -> list[str]` — Strip GH Actions timestamp prefix (`2026-01-15T10:30:45.1234567Z `), find the "Run implementation" step section between `##[group]` markers, return just the JSON lines
- `parse_impl_run_summary(lines: list[str]) -> ImplRunSummary` — Walk JSONL lines building the summary. Extract session_id from `system/init`, tool uses from `assistant` messages, final result from `result` message
- `format_summary(summary: ImplRunSummary) -> str` — Human-readable rendering

**Reuse:** `output_filter.py:summarize_tool_use()` for tool action summaries, `output_filter.py:extract_text_content()` for assistant text extraction.

### 2. `src/erk/cli/commands/exec/scripts/debug_impl_run.py` — Exec script

Thin CLI wrapper following existing exec script patterns.

```python
@click.command(name="debug-impl-run")
@click.argument("run_id")  # accepts numeric ID or full GH Actions URL
@click.option("--json", "output_json", is_flag=True)
@click.pass_context
def debug_impl_run(ctx: click.Context, *, run_id: str, output_json: bool) -> None:
```

Steps:
1. Parse `run_id` — if it's a URL, extract numeric ID via regex
2. `gh api repos/{owner}/{repo}/actions/runs/{run_id}/jobs --jq '.jobs[] | "\(.id)\t\(.name)"'` — find the "implement" job
3. `gh api repos/{owner}/{repo}/actions/jobs/{job_id}/logs` — fetch full logs
4. Call parser functions, output `format_summary()` or JSON

### 3. Register in `src/erk/cli/commands/exec/group.py`

Add import and `exec_group.add_command(debug_impl_run)`.

### 4. `tests/unit/core/test_impl_run_parser.py` — Parser unit tests

Pure function tests with realistic log fragments:
- `test_extract_stream_json_lines_strips_timestamps`
- `test_extract_stream_json_lines_finds_implementation_step`
- `test_parse_impl_run_summary_basic`
- `test_parse_impl_run_summary_with_errors`
- `test_format_summary`

### 5. `tests/unit/cli/commands/exec/scripts/test_debug_impl_run.py` — Exec script tests

Using Click CliRunner with ErkContext injection, mocking subprocess calls.

### 6. `.claude/commands/local/debug-impl-run.md` — Local slash command

Simple command that tells Claude to run `erk exec debug-impl-run` and interpret results. Knows how to find run IDs from URLs or PR context.

## Files to Modify

- `src/erk/cli/commands/exec/group.py` — Add import + `add_command`

## Implementation Order

1. Parser module + tests (pure logic, no deps)
2. Exec script + registration + tests
3. Local command

## Verification

1. Run parser unit tests: `pytest tests/unit/core/test_impl_run_parser.py`
2. Run exec script tests: `pytest tests/unit/cli/commands/exec/scripts/test_debug_impl_run.py`
3. Manual test against the actual failed run: `erk exec debug-impl-run 22902216182`
4. Verify output includes: session ID, model, tool call timeline, error about `${CLAUDE_SESSION_ID}`, files read vs modified

# Plan: Add Implementation Failure Summary to Remote CI

## Context

When `claude --print` exits with code 1 during remote implementation in `plan-implement.yml`, the only error message is "Implementation failed with exit code: 1". This is useless for debugging. The session JSONL is already captured and pushed to `planned-pr-context`, but nobody analyzes it. We want to use Haiku to produce a human-readable failure summary and surface it in **two places**: as a PR comment on the plan PR, and as a GitHub Actions job summary (visible on the Actions run page).

The existing `ci-generate-summaries` pattern (fetch logs -> truncate -> prompt Haiku -> post PR comment) provides the exact template to follow.

## Approach

Create a new exec command `erk exec summarize-impl-failure` that reads the raw session JSONL, extracts the tail, sends it to Haiku for diagnosis, posts the summary as a PR comment, and outputs it for use as a job summary. Add a workflow step that calls this on failure and writes the output to `$GITHUB_STEP_SUMMARY`.

## Files to Create

### 1. `.github/prompts/impl-failure-summarize.md`

Haiku prompt template. Focused on: what was the agent doing when it stopped, did it encounter an error or just stop, what files/operations were involved.

### 2. `src/erk/cli/commands/exec/scripts/summarize_impl_failure.py`

New exec script following the `ci_generate_summaries.py` pattern.

**CLI:** `erk exec summarize-impl-failure --session-file <path> --pr-number <N> [--exit-code <N>]`

**Key functions:**
- `_extract_session_tail(session_file: Path, *, max_entries: int) -> SessionTail | None` — Read JSONL, take last N entries (50), convert to compressed XML via `generate_compressed_xml()` from `preprocess_session.py`. Return dataclass with `total_events`, `last_entries_xml`, `has_result_event`.
- `_build_failure_prompt(*, session_tail: SessionTail, exit_code: int | None, prompts_dir: Path) -> str` — Load template, substitute variables. Follow `_build_summary_prompt()` pattern from `ci_generate_summaries.py` using `get_bundled_github_dir()`.
- `_post_failure_comment(*, pr_number: int, comment_body: str, cwd: Path) -> None` — Post via `run_subprocess_with_context` + `gh pr comment`.

**Flow:**
1. `require_cwd(ctx)`, `require_prompt_executor(ctx)`
2. Extract session tail (last 50 entries -> compressed XML)
3. If empty/None, post minimal "Session too short to analyze" comment
4. Build prompt from template
5. Call Haiku via `executor.execute_prompt()`
6. Build markdown comment with `## Implementation Failure Summary` header
7. Post to PR as comment
8. Print the same markdown to stdout (for workflow to capture and write to `$GITHUB_STEP_SUMMARY`)
9. Always exit 0 (diagnostic, never blocks workflow)

**Reuse:**
- `generate_compressed_xml()` from `preprocess_session.py` — converts JSONL entries to compact XML
- `get_bundled_github_dir()` from `erk.artifacts.paths` — locates prompt templates
- `require_prompt_executor()` from `erk_shared.context.helpers` — Haiku access
- `run_subprocess_with_context()` from `erk_shared.subprocess_utils` — `gh pr comment`

### 3. `tests/unit/cli/commands/exec/scripts/test_summarize_impl_failure.py`

Test pure functions: `_extract_session_tail` (empty, small, normal, large sessions), `_build_failure_prompt` (template substitution, fallback), comment body formatting.

## Files to Modify

### 4. `src/erk/cli/commands/exec/group.py`

Add import and registration:
```python
from erk.cli.commands.exec.scripts.summarize_impl_failure import summarize_impl_failure
# ...
exec_group.add_command(summarize_impl_failure, name="summarize-impl-failure")
```

### 5. `.github/workflows/plan-implement.yml`

Insert new step AFTER "Update plan header" (line ~313) and BEFORE "Handle implementation outcome" (line ~315):

```yaml
- name: Summarize implementation failure
  if: steps.implement.outputs.implementation_success != 'true' && steps.session.outputs.session_file
  continue-on-error: true
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GH_TOKEN: ${{ github.token }}
    SESSION_FILE: ${{ steps.session.outputs.session_file }}
    PR_NUMBER: ${{ inputs.pr_number }}
    EXIT_CODE: ${{ steps.implement.outputs.exit_code }}
  run: |
    SUMMARY=$(erk exec summarize-impl-failure \
      --session-file "$SESSION_FILE" \
      --pr-number "$PR_NUMBER" \
      --exit-code "$EXIT_CODE")
    echo "$SUMMARY" >> "$GITHUB_STEP_SUMMARY"
```

Key: `continue-on-error: true` so failures here don't block the workflow. The script posts a PR comment internally and prints the summary to stdout, which the workflow captures and writes to `$GITHUB_STEP_SUMMARY` for the Actions run page.

## Verification

1. **Unit tests:** Run `pytest tests/unit/cli/commands/exec/scripts/test_summarize_impl_failure.py`
2. **Local smoke test:** Create a sample session JSONL, run `erk exec summarize-impl-failure --session-file /tmp/test.jsonl --pr-number 9999 --exit-code 1` (will fail at Haiku call without API key but validates parsing)
3. **CI integration:** Dispatch a plan implementation that will fail and verify the PR comment appears

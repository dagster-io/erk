---
title: Implementation Failure Summarization
read_when:
  - "modifying failure summarization in plan-implement CI"
  - "understanding how implementation failures are analyzed"
  - "working with summarize-impl-failure exec script"
  - "debugging missing or incomplete failure summaries on PRs"
tripwires:
  - action: "modifying failure summarization prompt or model selection"
    warning: "The prompt template lives at .github/prompts/impl-failure-summarize.md. Changing the model from Haiku requires justifying cost vs. accuracy trade-off. Haiku was chosen for speed and cost on high-volume failure cases."
---

# Implementation Failure Summarization

When a remote implementation run (via `plan-implement.yml`) fails or exits non-zero, erk automatically generates a failure summary using Claude Haiku and posts it as a PR comment.

## Flow

```
plan-implement.yml (step ~325)
  ↓ on failure/non-zero exit
erk exec summarize-impl-failure --session-file <path> --pr-number <N> --exit-code <code>
  ↓
_extract_session_tail()   ← reads JSONL, runs Stage 1 mechanical reduction
  ↓
generate_compressed_xml() ← from erk_shared.learn.extraction.session_preprocessing
  ↓
_build_failure_prompt()   ← loads .github/prompts/impl-failure-summarize.md template
  ↓
executor.execute_prompt() ← calls claude --print with model=claude-haiku-4-5-20251001
  ↓
_build_comment_body()     ← assembles markdown with exit code + session event count
  ↓
_post_failure_comment()   ← gh pr comment --body ...
  ↓
click.echo()              ← stdout written to GITHUB_STEP_SUMMARY
```

## Exec Script

**Source**: `src/erk/cli/commands/exec/scripts/summarize_impl_failure.py`

Command: `erk exec summarize-impl-failure`

**Options**:

- `--session-file` (required): Path to the session JSONL file from the implementation run
- `--pr-number` (required): PR number to post the comment on
- `--exit-code`: Process exit code (for context in the summary)

**Always exits 0** — the tool is diagnostic and must never block the CI workflow.

## Session JSONL Capture

The implementation run's Claude session is captured as a JSONL file during the `plan-implement.yml` workflow. The tail of this file (last 50 events after Stage 1 reduction) is extracted for analysis.

Stage 1 reduction uses `process_log_content()` + `deduplicate_assistant_messages()` from `erk_shared.learn.extraction.session_preprocessing` — the same pipeline used for learn session processing.

## Prompt Template

**Location**: `.github/prompts/impl-failure-summarize.md`

The template uses two variables:

- `{{ EXIT_CODE }}`: The process exit code string
- `{{ SESSION_TAIL }}`: The compressed XML of the session tail

If the template file is missing, a minimal inline prompt is used as fallback.

## Model Selection: Haiku

`claude-haiku-4-5-20251001` is used (not Sonnet or Opus) because:

- **Cost**: Failure summarization runs on every failed implementation — at scale, Sonnet would be expensive
- **Speed**: Haiku is faster, reducing CI latency for failed runs
- **Accuracy trade-off**: For failure diagnosis (not code generation), Haiku's accuracy is sufficient

## Integration Point

The step is invoked in `.github/workflows/plan-implement.yml` at approximately line 325, in the failure-handling section:

```yaml
SUMMARY=$(erk exec summarize-impl-failure \
--session-file "$SESSION_FILE" \
--pr-number "$PR_NUMBER" \
--exit-code "$EXIT_CODE")
echo "$SUMMARY" >> "$GITHUB_STEP_SUMMARY"
```

The output goes to both the PR comment (via `gh pr comment`) and the GitHub Actions job summary (via `GITHUB_STEP_SUMMARY`).

## Related Documentation

- [Subprocess Wrappers](subprocess-wrappers.md) — `execute_prompt()` and stdin pattern
- [CI: GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) — General CI patterns

# Plan: Fix `ci-update-pr-body` to also update PR title

## Context

PR #7928 demonstrates a bug: the `/erk:git-pr-push` Claude agent generates a commit message influenced by its accumulated session context rather than strictly from the staged diff. This results in a wrong PR title. `ci-update-pr-body` later generates a **correct** summary from the actual GitHub API PR diff, but only calls `github.update_pr_body()` — it never corrects the title. The fix is to have `ci-update-pr-body` extract the title from the generated commit message and update both title and body.

## How the commit message prompt works

The prompt (`packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md`) produces output where:
- **Line 1** = PR title (e.g., "Remove node slug support from objective roadmap schema")
- **Lines 2+** = PR body (summary, files changed, key changes, etc.)

Currently `ci-update-pr-body` uses the entire Claude output as the `summary` field in the body. It should instead split: first line → title, rest → summary.

## Changes

### 1. Add `_parse_title_and_summary()` helper (`ci_update_pr_body.py`)

Extract first line as title, remainder as summary body:

```python
def _parse_title_and_summary(raw_output: str) -> tuple[str, str]:
    """Parse Claude's commit message output into title and summary.

    The commit message prompt produces: first line = title, rest = body.
    Returns (title, summary). If no newline found, title is the full output
    and summary is empty.
    """
    lines = raw_output.strip().split("\n", 1)
    title = lines[0].strip()
    summary = lines[1].strip() if len(lines) > 1 else ""
    return title, summary
```

### 2. Update `_update_pr_body_impl()` to use title

- After getting `result.output`, call `_parse_title_and_summary(result.output)` to split into `(title, summary)`
- Pass `summary` (not `result.output`) to `_build_pr_body()`
- Replace `github.update_pr_body(repo_root, pr_number, pr_body)` with `github.update_pr_title_and_body(repo_root=repo_root, pr_number=pr_number, title=title, body=BodyText(content=pr_body))`
- Add `BodyText` import from `erk_shared.gateway.github.types`

### 3. Update `UpdateSuccess` to include title

Add `title: str` field to `UpdateSuccess` so the JSON output reflects the new title for observability.

### 4. Update tests (`test_ci_update_pr_body.py`)

- Add test for `_parse_title_and_summary()` — multi-line input, single-line input
- Update `test_impl_success` to verify both title and body were updated (check `github.updated_pr_titles` in addition to `github.updated_pr_bodies`)
- Update `test_impl_draft_pr_preserves_metadata_and_adds_plan_section` similarly
- Update CLI tests to verify `title` field in JSON output

## Files Modified

1. `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` — core logic change
2. `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py` — test updates

## Verification

1. Run tests: `pytest tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`
2. Run ty/ruff on changed files

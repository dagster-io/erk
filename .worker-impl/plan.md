# Fix: Add fallback to `ci-update-pr-body` when AI summary fails

## Problem

After remote implementation completes, `erk exec ci-update-pr-body` should replace the "Queued for implementation" PR body with a summary. When it fails (Claude API error, large diff, etc.), the failure is silently swallowed by `continue-on-error: true` in the workflow, leaving the PR body stale.

## Root Cause

`ci_update_pr_body.py` has no fallback — if Claude fails OR the diff fetch fails, the command returns `UpdateError` and exits 1. The workflow step's `continue-on-error: true` hides this.

## Solution

Add a two-tier fallback inside `_update_pr_body_impl`:

1. **Primary**: AI-generated summary from PR diff (current behavior)
2. **Fallback**: Commit message from the implementation commit (via `git.commit.get_commit_messages_since`)
3. **Last resort**: Minimal static message

This ensures the PR body is always updated, regardless of Claude/diff failures.

## Files to Modify

### `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`

1. **Add `summary_source` field to `UpdateSuccess`**:

   ```python
   @dataclass(frozen=True)
   class UpdateSuccess:
       success: bool
       pr_number: int
       summary_source: Literal["ai", "commit-message", "minimal-fallback"]
   ```

2. **Extract `_try_ai_summary` helper** (returns `str | None`):
   - Takes executor, repo_root, diff_content, current_branch, parent_branch
   - Returns the AI output or None on any failure

3. **Add `_get_fallback_summary` function**:
   - Calls `git.commit.get_commit_messages_since(repo_root, parent_branch)`
   - Filters out noise commits: "Remove .worker-impl/", "Trigger CI workflows", "Update plan for issue", "Add plan for issue"
   - Returns joined meaningful commit messages, or None if none found

4. **Restructure `_update_pr_body_impl`**:
   - Make diff fetch non-fatal (catch RuntimeError, treat empty diff as None)
   - Try AI summary only if diff is available
   - Fall back to commit messages if AI fails
   - Fall back to minimal message if commit messages also fail
   - Only return `UpdateError` for `pr-not-found` or `github-api-failed` (the only truly unrecoverable errors)
   - Track which source was used in `summary_source`

### `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`

**Update existing tests** that now succeed via fallback instead of returning errors:

- `test_impl_empty_diff` — now succeeds with commit-message or minimal-fallback source
- `test_impl_claude_failure` — now succeeds with commit-message or minimal-fallback source
- `test_impl_claude_failure_truncates_long_stderr` — remove (error path no longer exists)
- `test_impl_claude_empty_output` — now succeeds with fallback

**Add new tests**:

- `test_get_fallback_summary_single_commit` — one meaningful commit returns it
- `test_get_fallback_summary_filters_noise` — filters .worker-impl/CI noise commits
- `test_get_fallback_summary_no_meaningful` — all noise returns None
- `test_get_fallback_summary_multiple` — multiple meaningful commits joined as bullets
- `test_impl_claude_failure_falls_back_to_commit_message` — Claude fails, commit message used, UpdateSuccess with source="commit-message"
- `test_impl_diff_unavailable_falls_back` — diff fetch raises, falls back to commit message
- `test_impl_all_fallbacks_fail_uses_minimal` — no diff, no commits, uses minimal message with source="minimal-fallback"
- `test_impl_success_reports_ai_source` — normal success has source="ai"

**Key test pattern**: Configure `FakeGit` with `commit_messages_since` parameter, `FakeGitHub` with `pr_diffs` and `_updated_pr_bodies` tracking, `FakePromptExecutor` with failing results.

## No Workflow Changes

The `.github/workflows/plan-implement.yml` step stays unchanged — `continue-on-error: true` remains as a safety net, but the command itself will almost never fail now.

## Verification

1. Run existing tests (scoped): `pytest tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`
2. Run type checker: `ty` on the modified files
3. Run linter: `ruff check` on modified files
4. Run formatter: `make prettier` (no docs changed, but just in case)

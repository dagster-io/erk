# Plan: Publish Draft PRs in `erk pr submit`

## Context

`erk pr submit` pushes code, creates or updates a PR, generates an AI description, and finalizes PR metadata. Currently, if the targeted PR is in **draft** status, the command leaves it as a draft. The Graphite path already handles draft → ready via `gt submit --publish`, but the core (non-Graphite) path has no such logic. The user wants `erk pr submit` to unconditionally publish draft PRs — across both paths.

## Approach

Add a draft-status check and `mark_pr_ready()` call inside the existing `finalize_pr()` pipeline step. This runs for all paths (Graphite and core) and is the natural place for all "finalize PR metadata" operations. Adding one `get_pr()` call for the draft check is acceptable (minimal extra API cost).

## Files to Change

### 1. `packages/erk-shared/src/erk_shared/gateway/github/fake.py`

Update `mark_pr_ready` from a no-op to a tracked mutation:

- Add `self._marked_pr_ready: list[int] = []` in `__init__` alongside `self._closed_prs`, `self._merged_prs`, etc.
- Update `mark_pr_ready` to append the PR number and update the in-memory `_pr_details` entry to `is_draft=False` (mirrors the pattern in `update_pr_title_and_body` which also updates in-memory state after mutation).
- Add `marked_pr_ready` property returning `list[int]` for test assertions.

### 2. `src/erk/cli/commands/pr/submit_pipeline.py`

In `finalize_pr()`, after `ctx.github.update_pr_title_and_body(...)` (currently ~line 661) and before the learn label check:

```python
# Publish draft PR if needed
pr_draft_check = ctx.github.get_pr(state.repo_root, state.pr_number)
if not isinstance(pr_draft_check, PRNotFound) and pr_draft_check.is_draft:
    click.echo(click.style("   Publishing draft PR...", dim=True))
    ctx.github.mark_pr_ready(state.repo_root, state.pr_number)
```

No imports needed — `PRNotFound` is already imported at the top of the file.

### 3. `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`

Add two tests following the established patterns (`_make_state`, `_pr_details`, `FakeGitHub`, `context_for_test`):

- **`test_publishes_draft_pr`**: Configure `_pr_details(is_draft=True)` in `FakeGitHub`, run `finalize_pr`, assert `42 in fake_github.marked_pr_ready`.
- **`test_does_not_publish_non_draft_pr`**: Configure `_pr_details(is_draft=False)` (default), run `finalize_pr`, assert `fake_github.marked_pr_ready == []`.

Note: `_pr_details()` helper in the test file already hard-codes `is_draft=False`. The new tests will need to pass `is_draft=True/False` explicitly, which requires adding an `is_draft` parameter to `_pr_details()`.

## Verification

Run the existing finalize_pr tests plus the new tests:

```bash
uv run pytest tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py -v
```

Then run the full submit pipeline tests for regression:

```bash
uv run pytest tests/unit/cli/commands/pr/submit_pipeline/ -v
```

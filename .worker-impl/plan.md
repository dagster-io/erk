# Fix: Graphite tracking divergence after commit amend in pr-submit

## Problem

`finalize_pr()` in `submit_pipeline.py` calls `amend_commit()` (line 664) **after** `gt submit` has already pushed and cached the commit SHA. This causes Graphite to detect the branch as "diverged from tracking" because its cached SHA no longer matches HEAD.

## Fix

Add a `retrack_branch()` call immediately after `amend_commit()` in `finalize_pr()`. This is a local-only operation that updates Graphite's cache to match the new HEAD SHA.

### File 1: `src/erk/cli/commands/pr/submit_pipeline.py`

After line 664 (`ctx.git.commit.amend_commit(state.repo_root, commit_message)`), add:

```python
# Fix Graphite tracking divergence caused by the amend
if ctx.graphite_branch_ops is not None:
    ctx.graphite_branch_ops.retrack_branch(state.repo_root, state.branch_name)
```

No divergence check needed — we know the amend just changed the SHA, and `retrack_branch` is idempotent.

### File 2: `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`

Add one test (Layer 4 business logic test over fakes):

- `test_retracks_graphite_after_amend` — verify `retrack_branch` is called after amend by checking `fake_graphite_branch_ops.retrack_branch_calls`. Uses the existing `context_for_test()` which already provides a `FakeGraphiteBranchOps` by default.

Access pattern: `ctx.graphite_branch_ops.retrack_branch_calls` provides mutation tracking.

## Why this approach

- Matches existing pattern in `sync_cmd.py:248-255`
- `retrack_branch` is local-only (no network), idempotent, and already implemented in the fake with mutation tracking
- `context_for_test()` already creates `FakeGraphiteBranchOps` by default — no test infrastructure changes needed
- Landing uses PR title from GitHub API, not local commit message, so remote having old message is harmless

## Verification

1. Run `pytest tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`
2. Run `ty` for type checking
3. Run `ruff check` for lint

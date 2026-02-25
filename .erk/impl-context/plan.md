# Fix get_diff_to_branch: two-dot to three-dot git diff

## Context

`get_diff_to_branch` uses `git diff {branch}..HEAD` (two-dot), which compares tree states at the two tips directly. When a feature branch hasn't been rebased onto latest master, this includes the inverse of commits on master that the branch doesn't have — producing a noisy diff with files unrelated to the PR (observed: 45 spurious files vs 3 actual changed files).

Three-dot (`git diff {branch}...HEAD`) diffs from the merge-base to HEAD, showing only changes introduced on the feature branch. This matches GitHub's PR diff behavior. The review prompt assembly already uses three-dot syntax, and the `large-diff-recovery.md` doc already shows three-dot — only the implementation is wrong.

The existing docstring's reasoning ("two-dot avoids rebased commits with different SHAs") confuses `git log` three-dot semantics with `git diff` three-dot semantics. For `git diff`, three-dot simply uses the merge-base as the comparison point.

## Changes

### 1. Fix git command and docstring in `real.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/real.py`

- Line 71: `f"{branch}..HEAD"` → `f"{branch}...HEAD"`
- Lines 63-68: Update docstring to explain three-dot merge-base semantics

### 2. Update ABC docstring in `abc.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/abc.py`

- Lines 69-70: Update docstring from "two-dot" to "three-dot" with correct explanation

## No changes needed

- `fake.py`, `dry_run.py`, `printing.py` — no syntax awareness, transparent delegation
- `count_commits_ahead`/`count_commits_behind` (rev-list) — two-dot is correct for commit counting
- `commit_ops/real.py` (git log) — two-dot is correct for log
- `large-diff-recovery.md` — already shows correct three-dot syntax
- `review/prompt_assembly.py` — already uses three-dot
- Callers (`submit_pipeline.py`, `diff_extraction.py`) — no syntax awareness
- No tests directly exercise `get_diff_to_branch`; fake is dict-based

## Verification

After the change, on a branch that has diverged from master:
- `git diff master...HEAD` should show only feature branch changes
- `git diff master..HEAD` (old behavior) would show spurious files from divergence
- Run CI to confirm no regressions

# Plan: Local Review Marker to Skip CI Reviews

## Context

Running `/local:code-review` locally produces the same results as CI code reviews, but there's no way to signal this to CI. Every push triggers full CI reviews even when the developer just ran them locally. This wastes CI minutes and slows down the feedback loop.

The goal: after local code review passes, mark the PR so CI skips redundant reviews. The marker is tied to a specific commit SHA so it auto-invalidates when new commits are pushed.

## Marker Format

HTML comment appended to PR body (invisible in rendered description):

```
<!-- erk:local-review-passed:<full-40-char-sha> -->
```

## Changes

### 1. New exec script: `set-local-review-marker`

**File:** `src/erk/cli/commands/exec/scripts/set_local_review_marker.py`

- Click command `set-local-review-marker` with `@click.pass_context`
- Auto-detects current branch via `require_git(ctx).branches.get_current_branch(cwd)`
- Gets HEAD SHA via `require_git(ctx).branches.get_branch_head(repo_root, branch)`
- Finds PR via `require_github(ctx).get_pr_for_branch(repo_root, branch)`
- If no PR found: outputs `{"success": false, "reason": "no_pr"}` and exits 0 (not an error)
- Reads current PR body from `PRDetails.body`
- Strips any existing `<!-- erk:local-review-passed:... -->` line via regex
- Appends new marker line
- Updates via `require_github(ctx).update_pr_body(repo_root, pr_number, new_body)`
- Outputs `{"success": true, "pr_number": N, "sha": "..."}`

### 2. Register exec script

**File:** `src/erk/cli/commands/exec/group.py`

- Import and register: `exec_group.add_command(set_local_review_marker, name="set-local-review-marker")`

### 3. Update local code-review command

**File:** `.claude/commands/local/code-review.md`

Add **Phase 4: Mark PR as Reviewed** after Phase 3:

- Only runs if ALL reviews passed (0 total violations)
- Runs `erk exec set-local-review-marker` via Bash
- Reports the result (marker set, or no PR found, or skipped due to violations)

### 4. Update CI workflow

**File:** `.github/workflows/code-reviews.yml`

Add a first step in the `discover` job (before checkout) that checks for the marker:

```yaml
- name: Check local review marker
  id: check_local_review
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    HEAD_SHA="${{ github.event.pull_request.head.sha }}"
    MARKER="<!-- erk:local-review-passed:${HEAD_SHA} -->"
    PR_BODY=$(gh pr view ${{ github.event.pull_request.number }} \
      --repo ${{ github.repository }} --json body -q .body)
    if echo "$PR_BODY" | grep -qF "$MARKER"; then
      echo "Local review marker found for HEAD ${HEAD_SHA:0:8} - skipping CI reviews"
      echo "skip=true" >> "$GITHUB_OUTPUT"
    else
      echo "skip=false" >> "$GITHUB_OUTPUT"
    fi
```

All subsequent steps in `discover` get `if: steps.check_local_review.outputs.skip != 'true'`.

Update `has_reviews` output to account for skip:
```yaml
has_reviews: ${{ steps.check_local_review.outputs.skip != 'true' && steps.discover.outputs.has_reviews == 'true' }}
```

### 5. Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_set_local_review_marker.py`

Test cases:
- Happy path: PR exists, marker set, body updated with marker appended
- No PR for branch: outputs success=false with reason
- Existing marker replaced: old marker stripped, new one appended
- Detached HEAD: graceful failure
- PR body with footer: marker appended correctly (doesn't break footer)

Uses `ErkContext.for_test()` with `FakeGitHub` and `FakeGit` for full gateway injection.

## Key Patterns to Follow

- **LBYL**: Check `isinstance(pr_result, PRNotFound)` before accessing fields
- **Frozen dataclasses**: Any new data types use `@dataclass(frozen=True)`
- **No default params**: All keyword args are required
- **Context injection**: `@click.pass_context` with `require_*` helpers
- **JSON output**: All exec scripts output JSON

## Verification

1. Run `erk exec set-local-review-marker` on a branch with a PR - check PR description has marker
2. Run `/local:code-review` with all reviews passing - verify marker auto-set
3. Push to GitHub - verify CI `code-reviews` workflow skips when marker matches HEAD
4. Push a new commit - verify CI runs reviews (SHA mismatch)
5. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_set_local_review_marker.py`

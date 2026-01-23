# Plan: Handle "No Code Changes" Gracefully in erk-impl Workflow

## Problem

When the erk-impl workflow runs but produces no code changes (e.g., duplicate plan, work already merged), it currently:
- Fails with `exit 1`
- Diagnostic info is buried in CI logs
- User must dig through workflow logs to understand what happened

## Solution

Make the workflow **succeed** and create an **informational PR** explaining why no changes were made. The user can review the PR and close it (along with the plan issue).

## Implementation

### 1. Add Label Definition

**File:** `packages/erk-shared/src/erk_shared/github/plan_issues.py`

Add after line 38 (after `_LABEL_ERK_OBJECTIVE`):

```python
_LABEL_NO_CHANGES = "no-changes"
_LABEL_NO_CHANGES_DESC = "Implementation produced no code changes"
_LABEL_NO_CHANGES_COLOR = "FFA500"  # Orange - attention needed
```

Add to `get_erk_label_definitions()` function.

### 2. Create New Exec Command

**File:** `src/erk/cli/commands/exec/scripts/handle_no_changes.py`

Command: `erk exec handle-no-changes`

Options:
- `--pr-number` (required): PR number to update
- `--issue-number` (required): Plan issue number
- `--behind-count` (required): How many commits behind base branch
- `--base-branch` (required): Base branch name
- `--recent-commits` (optional): Recent commits on base branch
- `--run-url` (optional): Workflow run URL

Behavior:
1. Build explanatory PR body with:
   - "No Code Changes" header
   - Diagnostic info (behind count, recent commits)
   - Next steps instructions
   - Link to plan issue
2. Update PR body via `github.update_pr_body()`
3. Add `no-changes` label via `github.add_label_to_pr()`
4. Mark PR ready for review via `gh pr ready`
5. Add comment to plan issue linking to PR
6. Exit with code 0 (success)

Follow pattern from `ci_update_pr_body.py`:
- Use `@click.pass_context` with `require_*` helpers
- Frozen dataclasses for result types
- JSON output

### 3. Register Command

**File:** `src/erk/cli/commands/exec/group.py`

Add import and register:
```python
from erk.cli.commands.exec.scripts.handle_no_changes import handle_no_changes
group.add_command(handle_no_changes)
```

### 4. Update Workflow

**File:** `.github/workflows/erk-impl.yml`

Replace "Validate implementation produced changes" step (lines 257-294):

```yaml
      - name: Handle implementation outcome
        id: handle_outcome
        if: steps.implement.outputs.implementation_success == 'true'
        env:
          BASE_BRANCH: ${{ inputs.base_branch }}
          ISSUE_NUMBER: ${{ inputs.issue_number }}
          PR_NUMBER: ${{ inputs.pr_number }}
          GH_TOKEN: ${{ github.token }}
        run: |
          # Check for changes excluding .worker-impl/ and .impl/
          CHANGES=$(git status --porcelain | grep -v '^\s*D.*\.worker-impl/' | grep -v '\.impl/' || true)

          if [ -z "$CHANGES" ]; then
            echo "No code changes detected, handling gracefully..."

            # Gather diagnostic info
            git fetch origin "$BASE_BRANCH" --quiet
            BEHIND_COUNT=$(git rev-list HEAD.."origin/$BASE_BRANCH" --count 2>/dev/null || echo "0")
            RECENT_COMMITS=$(git log HEAD.."origin/$BASE_BRANCH" --oneline --max-count=5 2>/dev/null || echo "")

            # Call exec command to handle no-changes scenario
            erk exec handle-no-changes \
              --pr-number "$PR_NUMBER" \
              --issue-number "$ISSUE_NUMBER" \
              --behind-count "$BEHIND_COUNT" \
              --base-branch "$BASE_BRANCH" \
              --recent-commits "$RECENT_COMMITS" \
              --run-url "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"

            echo "has_changes=false" >> $GITHUB_OUTPUT
          else
            echo "Implementation produced changes:"
            echo "$CHANGES"
            echo "has_changes=true" >> $GITHUB_OUTPUT
          fi
```

Update subsequent steps to check `has_changes == 'true'`:
- Line 299: "Submit branch with proper commit message"
- Line 332: "Mark PR ready for review"
- Line 340: "Update PR body with implementation summary"
- Line 353: "Trigger CI workflows"
- Line 367: "Trigger async learning"

### 5. Add Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py`

Test cases:
- PR body is updated with diagnostic content
- `no-changes` label is added
- PR is marked ready for review
- Issue comment is added
- Exits with code 0
- Handles missing optional arguments gracefully

Use `FakeGitHub` and `FakeGitHubIssues` for testability.

## PR Body Format

```markdown
## No Code Changes

Implementation completed but produced no code changes.

### Diagnosis

**Likely cause: Duplicate plan** - The work may already be merged to `master`.

Branch is **5 commits** behind `origin/master`.

**Recent commits on `master`:**
- abc1234 Fix the authentication bug
- def5678 Add user validation

### Next Steps

1. Review the recent commits above to check if the work is done
2. If done: Close this PR and the linked plan issue #456
3. If not done: Investigate why no changes were produced

---

Closes #456

[View workflow run](https://github.com/owner/repo/actions/runs/123456)
```

## Files to Modify

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/github/plan_issues.py` | Add label definition |
| `src/erk/cli/commands/exec/scripts/handle_no_changes.py` | Create new |
| `src/erk/cli/commands/exec/group.py` | Register command |
| `.github/workflows/erk-impl.yml` | Update validation step |
| `tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py` | Create new |

## Verification

1. Run `make fast-ci` to verify tests pass
2. Create a test scenario:
   - Create a plan issue for work that's already merged
   - Run `erk plan submit` to trigger workflow
   - Verify workflow succeeds
   - Verify PR has informational body and `no-changes` label
   - Verify PR is marked ready for review
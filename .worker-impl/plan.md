# Plan: Combine learn-async into erk-impl Workflow

## Summary

Merge the `learn-async.yml` workflow into `erk-impl.yml` so there's a single workflow for plan implementation. Documentation extraction (learn) will run after implementation and commit to the same PR branch.

## Current State

- `erk-impl.yml` runs implementation, then triggers `learn-async.yml` via `erk exec trigger-async-learn`
- `learn-async.yml` creates a **separate** branch/PR with generic commit message "Learn from plan #X"
- PR #5735 is an example of this poor experience

## Changes

### 1. Modify `.github/workflows/erk-impl.yml`

**Add learn step** after "Update PR body" (line ~369) and before "Trigger CI workflows" (line ~371):

```yaml
- name: Run learn workflow
  id: learn
  if: steps.implement.outputs.implementation_success == 'true' && steps.handle_outcome.outputs.has_changes == 'true' && (steps.submit.outcome == 'success' || steps.handle_conflicts.outcome == 'success')
  continue-on-error: true  # Learn failure shouldn't fail implementation
  env:
    CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
  run: |
    echo "Running learn workflow for plan #${{ inputs.issue_number }}..."
    claude --print \
      --model claude-haiku-4-5 \
      --output-format stream-json \
      --dangerously-skip-permissions \
      --verbose \
      "/erk:learn ${{ inputs.issue_number }}" || echo "Learn completed with exit: $?"

- name: Commit learn documentation
  if: steps.learn.outcome == 'success'
  continue-on-error: true
  env:
    SUBMITTED_BY: ${{ inputs.submitted_by }}
    BRANCH_NAME: ${{ steps.find_pr.outputs.branch_name }}
  run: |
    if [[ -n $(git status --porcelain docs/ .claude/) ]]; then
      git config user.name "$SUBMITTED_BY"
      git config user.email "$SUBMITTED_BY@users.noreply.github.com"
      git add docs/ .claude/
      git commit -m "Add documentation from plan #${{ inputs.issue_number }}"
      git push origin "$BRANCH_NAME"
      echo "Committed documentation changes"
    else
      echo "No documentation changes from learn"
    fi
```

**Remove** the "Trigger async learning" step (lines 385-393).

### 2. Delete `.github/workflows/learn-async.yml`

The workflow is no longer needed since learn runs inline in erk-impl.

### 3. Update `trigger_async.py` (optional)

Keep the function for `erk learn --async` CLI usage (local implementations), but update docstring to note that erk-impl now runs learn automatically.

## New Workflow Sequence

```
erk-impl.yml:
...
9. Submit branch with commit message
10. Handle merge conflicts if needed
11. Mark PR ready for review
12. Update PR body
13. NEW: Run learn (/erk:learn)
14. NEW: Commit docs if changes exist
15. Trigger CI workflows
```

## Edge Cases

- **Learn produces no changes**: Skip commit, continue
- **Learn command fails**: `continue-on-error: true` ensures workflow succeeds
- **No session data for learn**: Learn handles gracefully

## Files to Modify

| File | Action |
|------|--------|
| `.github/workflows/erk-impl.yml` | Add learn steps, remove async trigger |
| `.github/workflows/learn-async.yml` | Delete |

## Verification

1. Trigger erk-impl workflow on a test plan issue
2. Verify learn runs after implementation
3. Verify documentation changes (if any) are committed to same branch
4. Verify CI runs on combined implementation + docs
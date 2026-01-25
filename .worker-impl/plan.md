# Analysis: PR #6023 .worker-impl/ Not Cleaned Up

## Problem

PR #6023 still contains `.worker-impl/` files that should have been deleted:
- `.worker-impl/README.md`
- `.worker-impl/issue.json`
- `.worker-impl/plan.md`

## Root Cause: Non-Deterministic Agent Behavior + Broken Backup

The cleanup depends on **two mechanisms**, and both can fail:

### Mechanism 1: plan-implement Step 12 (Agent-Dependent)
Claude is supposed to run cleanup in Step 12 of `/erk:plan-implement`:
```bash
git rm -rf .worker-impl/ && git commit -m "Remove .worker-impl/..." && git push
```
**Problem:** This is non-deterministic - sometimes the agent follows Step 12, sometimes it doesn't.

### Mechanism 2: Workflow Backup (Broken by PR #4787)
The workflow stages deletion at lines 207-211, but PR #4787 added `git reset --hard` that erases it:
```bash
git fetch origin "$BRANCH_NAME"
git reset --hard "origin/$BRANCH_NAME"  # <-- DISCARDS STAGED DELETION
```

### Evidence
- **PR #6018**: Has "Remove .worker-impl/ after implementation" commit ← Step 12 ran ✓
- **PR #6023**: No cleanup commit ← Step 12 didn't run ✗

We've been "getting lucky" - when Step 12 runs, cleanup works. PR #6023 is an unlucky case where it didn't.

## Detailed Analysis

There are **two conflicting cleanup mechanisms** that both attempt to remove `.worker-impl/`:

### Mechanism 1: plan-implement Skill (Step 12)

In `.claude/commands/erk/plan-implement.md`, Step 12 says:
```bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  git commit -m "Remove .worker-impl/ after implementation"
  git push
fi
```

This is supposed to create a **separate cleanup commit** during plan-implement execution.

### Mechanism 2: Workflow erk-impl.yml (Lines 207-211)

In `.github/workflows/erk-impl.yml`, after plan-implement exits:
```bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  echo "Staged .worker-impl/ removal for commit"
fi
```

This **stages** the deletion, expecting `/erk:git-pr-push` to commit it.

## What Went Wrong

1. **plan-implement's Step 12 didn't run** - The cleanup in the skill likely didn't execute (perhaps Step 12 was never reached, or CI iteration took a different path)

2. **Workflow staged the deletion** (line 207-211) - Since `.worker-impl/` still existed, the workflow staged its removal

3. **git-pr-push didn't commit the deletion** - The `/erk:git-pr-push` skill's instructions focus on "meaningful implementation changes". When the Claude agent analyzed the staged diff, it likely saw only `.worker-impl/` deletions (cleanup artifacts) and either:
   - Decided there was "nothing meaningful" to commit
   - Or created a commit that focused only on the implementation changes, not the cleanup

4. **`git reset --hard` discarded the staged changes** - At line 381-382 in "Trigger CI workflows":
   ```bash
   git fetch origin "$BRANCH_NAME"
   git reset --hard "origin/$BRANCH_NAME"
   ```
   This reset discards any local staged changes that weren't pushed, permanently losing the `.worker-impl/` deletion.

## Evidence

Looking at the PR commits:
1. `Add plan for issue #5980` - plan
2. `Update plan for issue #5980 (rerun)` - plan update
3. `Add git lock check PreToolUse hook...` - implementation (**no .worker-impl/ cleanup**)
4. `Trigger CI workflows` - empty commit

No cleanup commit exists.

## The Core Bug

The `git reset --hard "origin/$BRANCH_NAME"` added in PR #4787 **destroys any local staged changes** that weren't committed and pushed. The staging at lines 207-211 is useless - it stages the deletion but then the reset erases it.

## Proposed Fix

Add an explicit cleanup step that commits and pushes `.worker-impl/` deletion **before** the `git reset --hard`:

```yaml
- name: Clean up .worker-impl/ after implementation commit
  if: steps.implement.outputs.implementation_success == 'true' && steps.handle_outcome.outputs.has_changes == 'true' && (steps.submit.outcome == 'success' || steps.handle_conflicts.outcome == 'success')
  env:
    BRANCH_NAME: ${{ steps.find_pr.outputs.branch_name }}
    SUBMITTED_BY: ${{ inputs.submitted_by }}
  run: |
    if [ -d .worker-impl/ ]; then
      git config user.name "$SUBMITTED_BY"
      git config user.email "$SUBMITTED_BY@users.noreply.github.com"
      git rm -rf .worker-impl/
      git commit -m "Remove .worker-impl/ after implementation"
      git push origin "$BRANCH_NAME"
    fi
```

Also remove the useless staging at lines 207-211 since it does nothing.

## Files to Modify

1. `.github/workflows/erk-impl.yml`:
   - Remove lines 207-211 (useless staging in "Run implementation" step)
   - Add new cleanup step between "Update PR body" and "Trigger CI workflows"

## Verification

After fix:
1. Submit a test plan via `erk plan submit`
2. Verify the PR has a cleanup commit removing `.worker-impl/`
3. Verify `.worker-impl/` is not in the final PR diff
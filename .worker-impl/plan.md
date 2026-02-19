# Plan: Migrate CI workflows: update plan-implement.yml concurrency groups and dispatch logic for PR-based plans

## Objective Context

This is node 2.4 of Objective #7419 (Migrate Plan System of Record from Issues to Draft PRs). The learn.yml migration (node 2.2, PR #7503) established the pattern: rename `issue_number` to `plan_id` throughout workflows and dispatch callers. This plan applies the same pattern to `plan-implement.yml` and its callers.

## Context & Understanding

The plan-implement.yml workflow currently uses `issue_number` as its primary identifier throughout. With the draft-PR plan backend, the plan identifier can be either a GitHub issue number OR a draft PR number. The existing exec scripts (create-worker-impl-from-issue, upload-session, update-plan-remote-session, handle-no-changes) already use PlanBackend abstraction internally, converting `issue_number` to `plan_id = str(issue_number)`. The workflow layer is the last piece that still hardcodes "issue" semantics.

**Key insight from learn.yml migration (PR #7503):** The migration renamed `issue_number` inputs to `plan_id` in the workflow YAML, updated environment variables, updated concurrency groups from `issue-` to `plan-` prefix, and updated all callers that dispatch the workflow.

**Current callers of plan-implement.yml:**
1. `src/erk/cli/commands/submit.py` - builds inputs dict with `"issue_number"` key (line 764)
2. `.github/workflows/one-shot.yml` - passes `issue_number` as `workflow_call` input (line 215)

**Exec scripts called from plan-implement.yml that accept `--issue-number`:**
- `create-worker-impl-from-issue` - Already uses PlanBackend internally
- `post-workflow-started-comment` - Uses GitHubIssues directly (posts comment to issue)
- `upload-session` - Already uses PlanBackend internally
- `update-plan-remote-session` - Already uses PlanBackend internally
- `handle-no-changes` - Already uses PlanBackend internally
- `ci-update-pr-body` - Does not use issue_number (uses PR number)
- `add-remote-execution-note` - Does not use issue_number (uses PR number)

## Changes

### Phase 1: Rename workflow input from `issue_number` to `plan_id`

#### File: `.github/workflows/plan-implement.yml`

**1a. Rename the workflow input parameter:**

In both `workflow_dispatch.inputs` and `workflow_call.inputs` sections:
- Rename `issue_number` to `plan_id`
- Update description from "GitHub issue number to implement" to "Plan identifier to implement"
- Keep `required: true` and `type: string`

**1b. Update `run-name`:**
- Change: `"${{ inputs.issue_number }}:${{ inputs.distinct_id }}"` to `"${{ inputs.plan_id }}:${{ inputs.distinct_id }}"`

**1c. Update concurrency group:**
- Change: `group: implement-issue-${{ inputs.issue_number }}` to `group: implement-plan-${{ inputs.plan_id }}`

**1d. Replace all `${{ inputs.issue_number }}` references with `${{ inputs.plan_id }}`:**

There are ~15 references throughout the file. Replace ALL of them. The full list (by line in current file):
- Line 2: `run-name`
- Line 78: `concurrency.group`
- Line 129: `env.ISSUE_NUMBER`
- Line 154: `env.ISSUE_NUMBER`
- Line 232: `env.ISSUE_NUMBER`
- Line 252: `env.ISSUE_NUMBER`
- Line 267: `env.ISSUE_NUMBER`
- Line 283: `env.ISSUE_NUMBER`
- Line 341: `env.ISSUE_NUMBER`
- Line 403: inline `${{ inputs.issue_number }}`

**1e. Rename environment variable `ISSUE_NUMBER` to `PLAN_ID` in all `env:` blocks:**

In every step that sets `ISSUE_NUMBER: ${{ inputs.issue_number }}`, change to `PLAN_ID: ${{ inputs.plan_id }}`.

Then update ALL `$ISSUE_NUMBER` usages in the `run:` scripts to `$PLAN_ID`.

Specific steps to update:

- **"Checkout implementation branch" step** (line 127):
  - `ISSUE_NUMBER` env -> `PLAN_ID`
  - `erk exec create-worker-impl-from-issue "$ISSUE_NUMBER"` -> `erk exec create-worker-impl-from-issue "$PLAN_ID"`
  - `gh issue comment "$ISSUE_NUMBER"` -> `gh issue comment "$PLAN_ID"` (Note: this is a fallback error path - `gh issue comment` works with both issue and PR numbers since GitHub treats them the same)
  - Commit message: `"Update plan for issue #$ISSUE_NUMBER (rerun)"` -> `"Update plan for #$PLAN_ID (rerun)"`

- **"Post workflow started comment" step** (line 152):
  - `ISSUE_NUMBER` env -> `PLAN_ID`
  - `--issue-number "$ISSUE_NUMBER"` -> `--issue-number "$PLAN_ID"`

- **"Run implementation" step** (line 209):
  - `ISSUE_NUMBER` env -> `PLAN_ID`
  - `"/erk:plan-implement $ISSUE_NUMBER"` -> `"/erk:plan-implement $PLAN_ID"`

- **"Upload session to gist" step** (line 248):
  - `ISSUE_NUMBER` env -> `PLAN_ID`
  - `--issue-number "$ISSUE_NUMBER"` -> `--issue-number "$PLAN_ID"`

- **"Update plan header with remote impl info" step** (line 262):
  - `ISSUE_NUMBER` env -> `PLAN_ID`
  - `--issue-number "$ISSUE_NUMBER"` -> `--issue-number "$PLAN_ID"`

- **"Handle implementation outcome" step** (line 278):
  - `ISSUE_NUMBER` env -> `PLAN_ID`
  - `--issue-number "$ISSUE_NUMBER"` -> `--issue-number "$PLAN_ID"`

- **"Submit branch" step** (line 333):
  - `ISSUE_NUMBER` env -> `PLAN_ID`
  - `"/erk:git-pr-push Implement issue #$ISSUE_NUMBER"` -> `"/erk:git-pr-push Implement plan #$PLAN_ID"`

- **"Update PR body" step** (line 394):
  - `--issue-number "${{ inputs.issue_number }}"` -> `--issue-number "${{ inputs.plan_id }}"`

### Phase 2: Update one-shot.yml caller

#### File: `.github/workflows/one-shot.yml`

**2a. Update the `implement` job's `workflow_call` inputs:**

The `implement` job (line 210) calls `plan-implement.yml` via `workflow_call`. Update the input mapping:
- Change: `issue_number: ${{ needs.plan.outputs.issue_number }}` to `plan_id: ${{ needs.plan.outputs.issue_number }}`

The `plan` job's outputs still produce `issue_number` from the one-shot planning step (this is correct - the one-shot planner always creates a GitHub issue). We just need to map it to the new input name.

### Phase 3: Update submit.py caller

#### File: `src/erk/cli/commands/submit.py`

**3a. Update the workflow inputs dict (line 762):**

In `_submit_single_issue()`, the `inputs` dict currently has:
```python
"issue_number": str(issue_number),
```

Change to:
```python
"plan_id": str(issue_number),
```

This is the only change needed in submit.py. The submit command always works with issue-based plans (it validates `erk-plan` label), so `issue_number` is always the correct plan_id.

### Phase 4: Update exec script CLI argument naming (optional but recommended)

The exec scripts called from the workflow accept `--issue-number` flags. These still work because the workflow passes the plan_id value through `--issue-number`. However, for consistency with the broader migration, we should rename these in a future step. **For this PR, we keep `--issue-number` flags as-is** since:
1. The exec scripts already convert to `plan_id = str(issue_number)` internally
2. Renaming exec script arguments is a larger change with its own test surface
3. This matches how the learn.yml migration was done (workflow first, scripts later)

## Files NOT Changing

- **Exec scripts** (`create_worker_impl_from_issue.py`, `post_workflow_started_comment.py`, `upload_session.py`, `update_plan_remote_session.py`, `handle_no_changes.py`, `ci_update_pr_body.py`, `add_remote_execution_note.py`, `register_one_shot_plan.py`): These already use PlanBackend internally. Their CLI flags (`--issue-number`) still accept the plan_id value correctly since it's passed as a string.
- **`.claude/commands/erk/plan-implement.md`**: The command reads from `.impl/` folder, not from workflow inputs. No changes needed.
- **`src/erk/cli/constants.py`**: Workflow filenames don't change.
- **`src/erk/cli/commands/one_shot_dispatch.py`**: Dispatches `one-shot.yml` (not `plan-implement.yml`). The one-shot workflow's inputs don't change.
- **`.github/workflows/learn.yml`**: Already migrated in node 2.2.
- **`.github/workflows/ci.yml`**, **`.github/workflows/docs.yml`**, etc.: Unrelated workflows.
- **CHANGELOG.md**: Never modify directly.

## Implementation Details

### Concurrency group naming convention

Following the learn.yml pattern:
- **Before:** `implement-issue-${{ inputs.issue_number }}`
- **After:** `implement-plan-${{ inputs.plan_id }}`

This ensures that concurrent dispatches for the same plan (whether issue-based or PR-based) cancel each other correctly.

### Backwards compatibility

There is none needed. The workflow input names are internal to the dispatch system. The two callers (submit.py and one-shot.yml) are updated in the same PR. No external systems reference these input names directly.

### Key decision: Keep `issue_title` input name

The `issue_title` input is used for display purposes in workflow steps. While we could rename it to `plan_title`, this would be a cosmetic change with no functional impact. **Keep as-is** to minimize diff size. The title comes from the issue regardless of backend.

### Key decision: Keep `--issue-number` on exec scripts

The exec script CLI arguments (`--issue-number`) are a separate migration surface. They accept string values that work as plan_id regardless of name. Renaming them would require updating tests, documentation, and error messages. **Defer to a future PR** to keep this change focused.

## Verification

1. **Grep for stale references**: After changes, grep plan-implement.yml for `issue_number` - should find ZERO matches (only `issue_title` should remain)
2. **Grep submit.py**: Verify the inputs dict uses `plan_id` key
3. **Grep one-shot.yml**: Verify the `implement` job passes `plan_id` (not `issue_number`)
4. **Run tests**: Execute `pytest tests/` to catch any test breakage (there may be tests that mock workflow dispatch inputs)
5. **Grep for test files**: Search `tests/` for `"issue_number"` in context of plan-implement workflow dispatch to update test fixtures
6. **Type check**: Run `ty` to verify no type errors

## Related Documentation

- `docs/learned/ci/plan-implement-workflow-patterns.md` - Workflow patterns
- `docs/learned/ci/plan-implement-change-detection.md` - Change detection logic
- `docs/learned/planning/plan-backend-migration.md` - PlanBackend migration guide
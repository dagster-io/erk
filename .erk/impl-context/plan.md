# Fix git-pr-push Metadata Destruction + Repair PR #7849

## Context

PR #7849 was dispatched from objective #7724 via the one-shot workflow. The plan-header metadata block (containing `objective_issue`, `last_dispatched_run_id`, `lifecycle_stage`, etc.) was correctly written to the PR body during planning. However, during the "Submit branch with proper commit message" step, the `/erk:git-pr-push` Claude session ran `gh pr edit 7849 --title "..." --body "..."` with a **completely new body**, destroying the plan-header. By the time `ci-update-pr-body --draft-pr` ran, `extract_metadata_prefix()` returned "" and the metadata was permanently lost.

This same bug affects **all** draft-PR plans submitted via the one-shot workflow — the `git-pr-push` step always overwrites the body.

## Part 1: Fix `/erk:git-pr-push` Command

**File:** `.claude/commands/erk/git-pr-push.md`

### Problem

When an existing PR is found (Step 6.5), the instructions say "skip Step 7 and go directly to Step 7.5". But Claude still runs `gh pr edit --body` before Step 7.5, overwriting the plan-header metadata. The instructions don't explicitly prohibit body editing for existing PRs.

### Fix

Add an explicit prohibition after Step 6.5's decision logic. When an existing PR is found:

1. **Do NOT edit the PR title or body** — the body may contain plan-header metadata blocks that must be preserved. The body will be updated by a subsequent `ci-update-pr-body` workflow step.
2. **Only push** (Step 5 already handles this) and **add footer** (Step 7.5).
3. Add a warning box making this crystal clear.

Specific changes to Step 6.5:
```
**Decision logic:**

- If `existing_pr` is empty or null: No existing PR, proceed to Step 7
- If `existing_pr` has data: PR exists, skip Step 7 and go directly to Step 7.5

> **CRITICAL: When an existing PR is found, do NOT run `gh pr edit --body` or `gh pr edit --title`.**
> The PR body may contain plan-header metadata blocks (`<!-- erk:metadata-block:plan-header -->`)
> that must be preserved. The body will be updated by a later workflow step (`ci-update-pr-body`).
> Only push code (Step 5) and add the checkout footer (Step 7.5).
```

Also update Step 7.5 to make the body-append safer — read the current body and append footer only (which it already does), but add a note:

```
> **Note:** When appending the footer, always read the current body first and append.
> Never replace the entire body — only append the footer to the existing content.
```

## Part 2: Repair PR #7849 Metadata

The plan-header block is completely missing from the PR body. Since `update-plan-header` requires an existing block to update, we need to manually reconstruct and prepend the plan-header using `gh api`.

### Fields to reconstruct

From the CI run logs and workflow data:
- `schema_version: '2'`
- `created_at`: Need to derive from PR creation time (use dispatch time ~`2026-02-22T13:58:00+00:00`)
- `created_by: schrockn`
- `branch_name: planned/O7724-erk-objective-pla-02-22-0858`
- `objective_issue: 7724`
- `last_dispatched_run_id: '22278544430'`
- `last_dispatched_node_id`: Need to fetch via `gh api`
- `last_dispatched_at`: ~`2026-02-22T14:04:11Z` (from register-one-shot-plan timestamp)
- `lifecycle_stage: implemented`
- All other fields: `null`

### Approach

1. Fetch the current PR body
2. Construct the plan-header metadata block string using the known values
3. Fetch the `last_dispatched_node_id` via `gh api repos/dagster-io/erk/actions/runs/22278544430 --jq '.node_id'`
4. Prepend the metadata block + separator (`\n\n---\n\n`) to the current body
5. Update the PR body via `gh api` or `gh pr edit --body-file`

We'll do this via shell commands — no code changes needed for the repair.

## Verification

1. After fixing `git-pr-push.md`: Review the diff to confirm the prohibition is clear
2. After repairing #7849: Run `erk exec get-plan-header 7849` (or check the TUI) to confirm objective_issue=7724 and run-id are visible
3. Check the TUI screenshot equivalent — the `obj` and `run-id` columns should populate for #7849

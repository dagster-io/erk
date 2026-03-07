---
title: Resubmission Workflows
category: pr-operations
read_when:
  - "modifying pr-submit command"
  - "working with was_created flag"
  - "handling PR resubmission"
last_audited: "2026-03-05 00:00 PT"
audit_result: clean
---

# Resubmission Workflows

The `/erk:pr-submit` command is idempotent — safe to re-run on existing PRs. It detects whether the PR already exists and adjusts its behavior accordingly.

## The `was_created` Flag

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, was_created field -->

`was_created` is a boolean on the submit pipeline result that indicates whether the PR was newly created or already existed. It's determined by LBYL: `get_pr_for_branch()` checks if a PR exists for the current branch before attempting creation.

- `was_created=True` — set when a new PR is created via `gt create` or `gh pr create`
- `was_created=False` — set when `get_pr_for_branch()` finds an existing PR

## Conditional Step Naming

The `/erk:pr-submit` command uses different step labels based on `was_created`:

| Step | New Submission (`was_created=True`) | Resubmission (`was_created=False`)      |
| ---- | ----------------------------------- | --------------------------------------- |
| 1    | "Created PR #N"                     | "Pushed changes (PR #N already exists)" |
| 3    | "Generate Title and Body"           | "Update Title and Body"                 |
| 4    | "Apply Description"                 | "Update Description"                    |
| 5    | Link PR to Objective                | **SKIPPED** (already linked)            |
| 6    | "PR created successfully"           | "PR updated successfully"               |

## Idempotency Guarantee

Re-running `/erk:pr-submit` on an existing PR:

1. Pushes new commits to the existing branch
2. Detects the PR already exists (`was_created=False`)
3. Regenerates and updates the PR title and body
4. Skips objective linking (already done on first submission)
5. Reports "PR updated successfully"

This makes it safe to re-submit after addressing review comments, adding more commits, or regenerating the PR description.

## Related Topics

- [PR Body Section Ordering](pr-body-section-ordering.md) - How the PR body is structured
- [PR Submit Phases](pr-submit-phases.md) - Full submit pipeline phases

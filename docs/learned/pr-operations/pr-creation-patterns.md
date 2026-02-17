---
title: PR Creation Decision Logic
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
read_when:
  - "creating a PR programmatically in any workflow"
  - "deciding whether to create vs update an existing PR"
  - "implementing a new exec script or pipeline step that touches PRs"
tripwires:
  - action: "calling create_pr without first checking get_pr_for_branch"
    warning: "Always LBYL-check for an existing PR before creating. Duplicate PRs cause confusion and orphaned state. See pr-creation-patterns.md."
  - action: "using raw gh pr view or gh pr create in Python code"
    warning: "Use the typed GitHub gateway (get_pr_for_branch, create_pr) instead of shelling out. The gateway returns PRDetails | PRNotFound for LBYL handling."
last_audited: "2026-02-16 14:25 PT"
audit_result: clean
---

# PR Creation Decision Logic

Every workflow that creates PRs programmatically must handle an existing PR for the same branch. Creating a duplicate causes orphaned PRs and confused reviewers. This document captures the cross-cutting check-before-create pattern and the three strategies callers choose after the check.

## The Core Pattern: LBYL via Discriminated Union

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/abc.py, GitHub.get_pr_for_branch -->

All PR creation sites use `GitHub.get_pr_for_branch()`, which returns `PRDetails | PRNotFound` — a discriminated union that forces callers to handle both cases. This is the LBYL mechanism: check before you create, using `isinstance` to branch on the result.

**Why not exceptions?** Erk uses LBYL everywhere. A missing PR is an expected condition, not an error. Using `isinstance` checks keeps the control flow explicit and avoids try/except for non-exceptional situations.

## Three Strategies After Detection

Different workflows need different behavior when a PR already exists:

| Strategy       | When PR exists                 | When no PR          | Used by                     |
| -------------- | ------------------------------ | ------------------- | --------------------------- |
| **Reject**     | Raise error, refuse to proceed | Create new PR       | Plan review PR creation     |
| **Update**     | Edit title/body of existing PR | Create new PR       | Submit pipeline (core flow) |
| **Query-only** | Use existing PR's details      | Return error result | PR sync, PR check, landing  |

### Why "Reject" for plan review PRs

<!-- Source: src/erk/cli/commands/exec/scripts/plan_create_review_pr.py, _create_review_pr_impl -->

Plan review PRs are structurally unique — one per plan issue, with specific title prefixes and labels. Creating a second would indicate a workflow bug (the branch was reused or the previous review wasn't cleaned up). Rejecting with `pr_already_exists` surfaces the real problem instead of silently creating a duplicate.

### Why "Update" for the submit pipeline

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _core_submit_flow -->

The submit pipeline's purpose is to get the branch's PR into a good state — whether that means creating one or enriching an existing one. When a PR exists, it preserves the PR number, adds missing footer metadata, and continues through the remaining pipeline phases (diff extraction, AI description, finalization). This is the most common path because agents often re-run `erk pr submit` on the same branch.

## Stacked PR Constraint

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _core_submit_flow -->

When creating a PR in the core (non-Graphite) flow, the pipeline checks whether the parent branch has a PR. If the branch is part of a Graphite stack but the parent has no PR, creation is blocked with guidance to use `gt submit -s` instead. This prevents creating a child PR with an invalid base branch, which GitHub would target against trunk instead of the parent.

## Anti-Patterns

**Using `gh pr view` exit codes in Python**: The current codebase never shells out to `gh pr view` to detect existing PRs. The typed gateway provides compile-time safety via the union return type. Shelling out loses type information and introduces parsing fragility.

**Creating first, deduplicating later**: Some workflows are tempted to create the PR optimistically and handle "already exists" errors. This fails because GitHub happily creates duplicate PRs for the same branch — there's no uniqueness constraint to catch you.

## Related Topics

- [PR Submit Workflow Phases](pr-submit-phases.md) — Full pipeline context for the update strategy
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — The broader pattern behind `PRDetails | PRNotFound`
- [Draft PR Handling](draft-pr-handling.md) — How plan review PRs use draft state

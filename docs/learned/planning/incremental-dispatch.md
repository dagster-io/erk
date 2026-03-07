---
title: Incremental Dispatch Workflow
read_when:
  - "dispatching implementation against an existing PR"
  - "adding a local plan to an existing PR for remote implementation"
  - "working with incremental-dispatch exec script or slash command"
tripwires:
  - action: "dispatching implementation against an existing PR"
    warning: "Use incremental-dispatch, not regular dispatch. Incremental dispatch does NOT require the erk-plan label — just an OPEN PR. It uses provider='incremental-dispatch' vs 'github-draft-pr'. See incremental-dispatch.md."
---

# Incremental Dispatch Workflow

Dispatch a local plan against an existing PR for remote implementation, without requiring the `erk-plan` label.

## What vs Regular Dispatch

| Aspect         | Regular Dispatch               | Incremental Dispatch              |
| -------------- | ------------------------------ | --------------------------------- |
| Input          | Plan number (draft PR)         | Local plan file + PR number       |
| Label required | `erk-plan`                     | None (just OPEN)                  |
| Provider       | `github-draft-pr`              | `incremental-dispatch`            |
| Use case       | New plan -> new implementation | Additional changes to existing PR |

## Workflow

1. **Slash command** (`/erk:pr-incremental-dispatch`) prompts user for plan content and target PR
2. **Exec script** (`erk exec incremental-dispatch`) receives `--plan-file` and `--pr` arguments
3. Script validates PR is OPEN, syncs branch, commits `.erk/impl-context/` files with `provider="incremental-dispatch"`
4. Triggers `plan-implement.yml` workflow via GitHub Actions dispatch

## CI Workflow Support

<!-- Source: .github/workflows/plan-implement.yml:138-171, "Checkout implementation branch" step -->

The `plan-implement.yml` workflow's "Checkout implementation branch" step (line 138) detects pre-committed `.erk/impl-context/` on the branch by checking if `plan.md` exists, and conditionally skips plan recreation. This is the key difference: regular dispatch creates impl-context during the workflow, while incremental dispatch pre-commits it.

## Key Files

- **Exec script:** `src/erk/cli/commands/exec/scripts/incremental_dispatch.py`
- **Slash command:** `.claude/commands/erk/pr-incremental-dispatch.md`
- **CI workflow:** `.github/workflows/plan-implement.yml`

## Branch Handling

Uses the same [checked-out branch handling pattern](../architecture/checked-out-branch-handling.md) as regular dispatch — detects whether the target branch is checked out in a worktree and uses `update_local_ref()` instead of `create_branch()` when needed.

## Related Topics

- [Checked-Out Branch Handling](../architecture/checked-out-branch-handling.md) — shared branch sync pattern
- [Planned PR Lifecycle](planned-pr-lifecycle.md) — full plan lifecycle documentation

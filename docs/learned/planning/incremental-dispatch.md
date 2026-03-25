---
title: Incremental Dispatch Workflow
read_when:
  - "dispatching implementation against an existing PR"
  - "adding a local plan to an existing PR for remote implementation"
  - "working with incremental-dispatch exec script or slash command"
tripwires:
  - action: "dispatching implementation against an existing PR"
    warning: "Use incremental-dispatch, not regular dispatch. Incremental dispatch does NOT require the erk-pr label — just an OPEN PR. It uses provider='incremental-dispatch' vs 'github-draft-pr'. See incremental-dispatch.md."
---

# Incremental Dispatch Workflow

Dispatch a local plan against an existing PR for remote implementation, without requiring the `erk-pr` label.

## What vs Regular Dispatch

| Aspect         | Regular Dispatch               | Incremental Dispatch              |
| -------------- | ------------------------------ | --------------------------------- |
| Input          | Plan number (draft PR)         | Local plan file + PR number       |
| Label required | `erk-pr`                       | None (just OPEN)                  |
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

Uses `sync_branch_to_sha()` at `incremental_dispatch.py:113` to sync the target branch to a known remote SHA before committing impl-context files. This is a separate code path from `dispatch_cmd.py` (both call the same function but in different contexts).

`sync_branch_to_sha` detects whether the target branch is checked out in a worktree:

- Not checked out: uses `update_local_ref()` directly
- Checked out: uses `reset_hard()` (rejects dirty worktrees with `SystemExit(1)`)

See [sync-branch-to-sha-pattern.md](../architecture/sync-branch-to-sha-pattern.md) for full details.

## Related Topics

- [sync_branch_to_sha Pattern](../architecture/sync-branch-to-sha-pattern.md) — branch sync used at incremental_dispatch.py:113
- [Planned PR Lifecycle](planned-pr-lifecycle.md) — full plan lifecycle documentation

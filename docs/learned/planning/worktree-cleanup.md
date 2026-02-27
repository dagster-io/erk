---
title: ".erk/impl-context/ Cleanup Discipline"
read_when:
  - cleaning up .erk/impl-context/ after plan implementation
  - debugging leftover .erk/impl-context/ artifacts in a PR
  - deciding whether to auto-remove an implementation folder
tripwires:
  - action: "automatically removing .erk/impl-context/ folder"
    warning: "NEVER auto-delete .erk/impl-context/ before implementation completes. It belongs to the user for plan-vs-implementation review. Only remove after CI passes."
  - action: "staging .erk/impl-context/ deletion without an immediate commit"
    warning: "A downstream `git reset --hard` will silently discard staged-only deletions. Always commit+push cleanup atomically. See reliability-patterns.md."
  - action: "removing .erk/impl-context/ during implementation (before CI passes)"
    warning: "The folder is load-bearing during implementation — Claude reads from it. Only remove after implementation succeeds and CI passes."
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
---

# .erk/impl-context/ Cleanup Discipline

The `.erk/impl-context/` folder serves implementation plans and has specific ownership and lifecycle rules that must be understood to avoid CI failures or lost context.

## What is .erk/impl-context/

The `.erk/impl-context/` folder is the implementation staging directory that contains plan content and metadata for the current implementation work:

| Aspect           | Details                                     |
| ---------------- | ------------------------------------------- |
| **Created by**   | Plan submission workflows (`erk pr submit`) |
| **Git status**   | Committed to branch, visible in PR          |
| **Owner**        | Workflow automation and Claude              |
| **Cleanup**      | Automatic after CI passes                   |
| **Review value** | Plan content for PR reviewers               |

<!-- Source: packages/erk-shared/src/erk_shared/impl_context.py, module docstring -->
<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, module docstring -->

The `.erk/impl-context/` folder is a transient coordination artifact used during plan submission and removed after implementation begins. See `impl_context.py` and `impl_folder.py` for the creation/removal APIs.

## Why .erk/impl-context/ Must Be Removed

Left-behind `.erk/impl-context/` folders cause concrete downstream failures:

1. **Prettier CI failures** — `.erk/impl-context/*.md` files trigger formatter checks on plan content that was never intended for formatting validation
2. **Stale state confusion** — Future implementations on the same branch may read outdated plan metadata
3. **PR noise** — Reviewers see transient workflow artifacts in the diff

## Cleanup Timing

Remove `.erk/impl-context/` only after all three conditions are met:

1. Implementation complete (all plan phases executed)
2. CI passes (tests, linting, type checking)
3. Implementation changes committed and pushed

**Never remove during implementation** — Claude reads from `.erk/impl-context/` throughout the implementation. Removing it mid-implementation prevents reruns from accessing plan content and causes failures.

**Exception: Workflow pre-implementation removal.** The `plan-implement.yml` workflow removes `.erk/impl-context/` from git immediately after copying it to `.erk/impl-context/` (branch-scoped), _before_ the implementation agent starts. This is safe because:

1. The copy to `.erk/impl-context/<branch>/` has already completed — the agent reads from there, not from the staging directory
2. The workflow regenerates the staging `.erk/impl-context/` from the issue on every run via `erk exec create-impl-context-from-plan`, so reruns are unaffected
3. Early removal prevents the staging directory from leaking into squash merges (the original bug this fix addresses)

## The Multi-Layer Cleanup Architecture

Cleanup uses three independent layers because no single layer is reliable on its own. This was learned through production failures — see [reliability-patterns.md](reliability-patterns.md) for the full case study.

| Layer                    | Mechanism                                      | Why it can fail                                     |
| ------------------------ | ---------------------------------------------- | --------------------------------------------------- |
| 1. Agent instruction     | `/erk:plan-implement` tells Claude to clean up | Context limits, misinterpretation                   |
| 2. Workflow staging      | `git rm` without immediate commit              | Silently discarded by downstream `git reset --hard` |
| 3. Dedicated commit step | Atomic remove + commit + push                  | Only fails if step condition is wrong               |

**Only Layer 3 is deterministic.** Layers 1 and 2 reduce how often Layer 3 needs to act, but cannot replace it.

<!-- Source: .github/workflows/plan-implement.yml, Clean up .erk/impl-context/ after implementation -->
<!-- Source: .github/workflows/pr-address.yml, Clean up plan staging dirs if present -->

See the "Clean up .erk/impl-context/ after implementation" step in `.github/workflows/plan-implement.yml` for the production Layer 3 implementation.

The `pr-address.yml` workflow also includes a cleanup step ("Clean up plan staging dirs if present") that removes `.erk/impl-context/` after Claude addresses review comments but before pushing. This prevents the folder from persisting when `pr-address` pushes changes to a branch that already contains it.

## Anti-Patterns

**Staging without commit before reset** — The most common failure mode. A workflow step runs `git rm -rf .erk/impl-context/` and stages the change, but a later step runs `git reset --hard` (e.g., to sync with remote), silently discarding the staged deletion. The fix is always: commit and push cleanup atomically before any step that might reset. See [plan-implement-workflow-patterns.md](../ci/plan-implement-workflow-patterns.md) for the detailed pattern.

**Auto-deleting .erk/impl-context/ before cleanup step** — `.erk/impl-context/` must persist through implementation so that reruns can access plan metadata. Only the final cleanup step should remove it, and only after CI passes.

**Removing .erk/impl-context/ before CI passes** — The cleanup step's condition gates on implementation success AND CI success. Removing before CI passes means a failed CI rerun can't access the plan metadata it needs for diagnostics. (Exception: the workflow's pre-implementation removal step — see "Cleanup Timing" above.)

## Diagnosing Leftover .erk/impl-context/

If `.erk/impl-context/` appears in a PR after implementation:

1. **Check workflow run logs** — Did the cleanup step run? Look for "Clean up .erk/impl-context/" in the step list
2. **Check step conditions** — The cleanup step requires `implementation_success == 'true'` AND either submit or conflict resolution succeeded
3. **Check for `git reset --hard`** — A reset after staging but before commit is the most common silent failure

Recovery is straightforward: `git rm -rf .erk/impl-context/` followed by commit and push. The key is diagnosing why automated cleanup failed to prevent recurrence.

## Related Documentation

- [reliability-patterns.md](reliability-patterns.md) — Multi-layer cleanup resilience and the commit-before-reset rule
- [plan-implement-workflow-patterns.md](../ci/plan-implement-workflow-patterns.md) — Step ordering constraints in the plan-implement workflow
- [lifecycle.md](lifecycle.md) — Full plan lifecycle including Phase 5 cleanup

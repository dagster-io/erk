---
title: ".erk/impl-context/ vs .impl/ Cleanup Discipline"
read_when:
  - cleaning up .erk/impl-context/ after plan implementation
  - debugging leftover .erk/impl-context/ artifacts in a PR
  - deciding whether to auto-remove an implementation folder
tripwires:
  - action: "automatically removing .impl/ folder"
    warning: "NEVER auto-delete .impl/. It belongs to the user for plan-vs-implementation review. Only .erk/impl-context/ is auto-cleaned."
  - action: "staging .erk/impl-context/ deletion without an immediate commit"
    warning: "A downstream `git reset --hard` will silently discard staged-only deletions. Always commit+push cleanup atomically. See reliability-patterns.md."
  - action: "removing .erk/impl-context/ during implementation (before CI passes)"
    warning: "The folder is load-bearing during implementation — Claude reads from it (via copy to .impl/). Only remove after implementation succeeds and CI passes."
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
---

# .erk/impl-context/ vs .impl/ Cleanup Discipline

Two folders serve implementation plans, but they have fundamentally different ownership models and lifecycle rules. Confusing them causes either lost user context (.impl/ deleted) or CI failures (.erk/impl-context/ left behind).

## Why Two Folders Exist

The split exists because remote (GitHub Actions) and local implementations have different trust models:

| Aspect           | `.impl/`                          | `.erk/impl-context/`                      |
| ---------------- | --------------------------------- | ----------------------------------------- |
| **Created by**   | Local agent or copied from remote | `erk plan submit` (automation)            |
| **Git status**   | In `.gitignore`, never committed  | Committed to branch, visible in PR        |
| **Owner**        | Human user                        | Workflow automation                       |
| **Cleanup**      | Manual only, never auto-deleted   | Automatic after CI passes                 |
| **Review value** | High — plan vs implementation     | None — plan content lives in GitHub issue |

<!-- Source: packages/erk-shared/src/erk_shared/impl_context.py, module docstring -->
<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, module docstring -->

The ownership distinction drives everything: `.impl/` is the user's working context (preserved indefinitely), while `.erk/impl-context/` is a transient coordination artifact (deleted as soon as its job is done). See `impl_context.py` and `impl_folder.py` for the creation/removal APIs.

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

**Never remove during implementation** — the workflow copies `.erk/impl-context/` to `.impl/` at the start, and Claude reads from `.impl/` throughout. Removing `.erk/impl-context/` mid-implementation doesn't break Claude's run, but it prevents reruns from refreshing plan content.

**Exception: Workflow pre-implementation removal.** The `plan-implement.yml` workflow removes `.erk/impl-context/` from git immediately after copying it to `.impl/`, _before_ the implementation agent starts. This is safe because:

1. The copy to `.impl/` has already completed — the agent reads from `.impl/`, not `.erk/impl-context/`
2. The workflow regenerates `.erk/impl-context/` from the issue on every run via `erk exec create-impl-context-from-plan`, so reruns are unaffected
3. Early removal prevents `.erk/impl-context/` from leaking into squash merges (the original bug this fix addresses)

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

**Auto-deleting .impl/** — `.impl/` belongs to the user. It preserves the original plan for comparison against implementation, and deleting it removes context the user may need for review or future reference. Never add automation that removes `.impl/`.

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

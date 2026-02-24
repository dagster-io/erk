---
title: Convergence Points Architecture
read_when:
  - "refactoring a command with multiple setup paths that share cleanup"
  - "adding a new entry path to an existing multi-path command"
  - "debugging cleanup that runs for some paths but not others"
tripwires:
  - action: "adding a new setup path to a command with existing cleanup"
    warning: "Ensure the new path calls the same convergence function. Multiple setup paths must converge at a single cleanup point to prevent resource leaks."
---

# Convergence Points Architecture

When multiple code paths must share a single cleanup or teardown operation, extract the shared logic to a **convergence point** — a standalone function called by all paths after their divergent setup completes.

## The Problem

Commands with multiple entry paths (e.g., planned-PR setup vs issue-based setup) tend to duplicate cleanup logic or, worse, skip it in some paths. This causes resource leaks when one path is tested but another isn't.

## Pattern

```
Path A (setup) ──┐
                  ├──▶ Convergence Point (cleanup/teardown)
Path B (setup) ──┘
```

1. Each setup path handles its own initialization
2. All paths write to a shared intermediate state (e.g., `.impl/` folder)
3. A single convergence function handles cleanup regardless of which path ran

## Canonical Example: Plan Implementation Setup

`src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` has two setup paths:

- `_setup_planned_pr_plan()` — fetches plan from draft PR via `github.get_pr()`
- `_setup_issue_plan()` — fetches plan from issue via `plan_backend.get_plan()`

Both paths create identical `.impl/` folder contents. Neither path deletes `.erk/impl-context/` — that cleanup is deferred to the convergence point in `/erk:plan-implement` Step 2d:

```bash
git rm -rf .erk/impl-context/ && git commit && git push
```

The cleanup is intentionally separated from setup so that:

- CI validation can run between setup and cleanup
- The cleanup commit is separate from the implementation commit
- Rerunning cleanup is idempotent (safe if `.erk/impl-context/` is already gone)

## Implementation Checklist

When adding a new setup path to a command with existing convergence:

1. Identify the convergence point (the shared cleanup/teardown)
2. Ensure the new path produces the same intermediate state as existing paths
3. Do NOT add cleanup logic to the new path — route through the convergence point
4. Add tests that exercise the new path through to convergence

## Related Documentation

- [Plan Lifecycle](../planning/lifecycle.md) — Phase 5 cleanup sequence
- [Planned PR Backend](../planning/planned-pr-backend.md) — Planned-PR setup path details

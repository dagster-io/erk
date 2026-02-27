---
title: Plan Execution Patterns
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
read_when:
  - "implementing a plan from a GitHub issue"
  - "understanding branch naming and worktree isolation"
  - "designing PR submission workflows for plans"
---

# Plan Execution Patterns

Patterns for executing plans: from issue preparation through PR submission.

## Branch Naming Conventions

Plan branches follow the pattern `plnd/<slug>-<timestamp>`:

- `plnd/consolidated-learn-docs-01-15-1430` — slugified title with timestamp
- The `plnd/` prefix identifies planned PR branches
- `plan-ref.json` is the sole source of truth for plan-to-branch mapping

**Legacy format:** Older plans may use the `P<issue-number>-<slug>` pattern (e.g., `P6967-consolidated-learn-docs`). The `P{issue}-` prefix is considered legacy.

## Worktree Isolation

Each plan implementation runs in an isolated worktree:

1. `erk br co --for-plan <issue-number>` creates a new worktree from the plan issue
2. The worktree gets its own `.erk/impl-context/` folder with the plan content
3. Implementation happens entirely within the worktree
4. After PR lands, the worktree is cleaned up

### Why Isolation?

- Prevents interference between concurrent implementations
- Allows easy rollback (delete the worktree)
- Keeps the main worktree clean for other work

## PR Submission Workflow

After implementation:

1. `erk pr submit` — commits, pushes, and creates/updates the PR
2. The PR description is generated from the plan content
3. If the plan has a GitHub issue, the PR links to it

## .erk/impl-context/ Folder Lifecycle

1. **Created**: by `erk exec setup-impl-from-pr` or manually
2. **Contains**: `plan.md` (immutable) and `plan-ref.json` (tracking)
3. **Preserved**: through implementation — never deleted by agents
4. **Committed**: as part of the PR for reviewer context
5. **Cleaned up**: after PR lands (during branch deletion)

## Related Documentation

- [Planning Workflow](workflow.md) — .erk/impl-context/ folder structure and commands
- [Plan Lifecycle](lifecycle.md) — Complete lifecycle from creation through merge

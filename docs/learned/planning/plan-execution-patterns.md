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

Plan branches follow the pattern `P<issue-number>-<slug>`:

- `P6967-consolidated-learn-docs` — issue #6967, slugified title
- The `P` prefix enables learn plan detection during landing
- `extract_leading_issue_number()` extracts the number from branch names

## Worktree Isolation

Each plan implementation runs in an isolated worktree:

1. `erk br co --for-plan <issue-number>` creates a new worktree from the plan issue
2. The worktree gets its own `.impl/` folder with the plan content
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

## .impl/ Folder Lifecycle

1. **Created**: by `erk exec setup-impl-from-issue` or manually
2. **Contains**: `plan.md` (immutable) and `plan-ref.json` (tracking)
3. **Preserved**: through implementation — never deleted by agents
4. **Committed**: as part of the PR for reviewer context
5. **Cleaned up**: after PR lands (during branch deletion)

## Related Documentation

- [Planning Workflow](workflow.md) — .impl/ folder structure and commands
- [Plan Lifecycle](lifecycle.md) — Complete lifecycle from creation through merge

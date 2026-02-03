---
title: Git-Only PR Submission Workflow
read_when:
  - "submitting PRs without Graphite"
  - "using /erk:git-pr-push command"
  - "understanding PR creation workflows"
last_audited: "2026-02-03"
audit_result: edited
---

# Git-Only PR Submission Workflow

## When to Use Git-Only vs. Graphite

### Git-Only (`/erk:git-pr-push`)

- No stacks, single feature branch
- Remote execution (GitHub Actions — Graphite not available)
- Direct to main/master, quick submission

### Graphite (`gt submit`)

- Stacked/dependent PRs
- Local development with stack management
- Complex PR dependencies

## Comparison

| Aspect          | Git-Only (`/erk:git-pr-push`) | Graphite (`gt submit`)      |
| --------------- | ----------------------------- | --------------------------- |
| Stacking        | No                            | Yes                         |
| Branch creation | Manual (`git branch`)         | Managed (`gt create`)       |
| PR creation     | `gh pr create`                | `gt submit`                 |
| Issue linking   | Automatic (`Closes #N`)       | Manual or via `gt finalize` |
| Use case        | Simple, remote execution      | Complex, local development  |
| Dependencies    | None (just git + gh CLI)      | Graphite tool required      |

## PR Validation

Run `erk pr check` after creating a PR. It validates:

- **Checkout footer** exists (enables `erk pr checkout`)
- **Issue linkage** (`Closes #N` in commit message)
- **PR body format** (title, description, test plan)

## Reference

- **Command**: `.claude/commands/erk/git-pr-push.md`
- **Graphite skill**: `.claude/skills/gt/`

## Related Documentation

- [Git-PR-Push Command](../../../.claude/commands/erk/git-pr-push.md) - Full command reference

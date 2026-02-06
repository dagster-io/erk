---
title: PR Submission Workflow (Git-Only Path)
read_when:
  - creating PRs via git commands and gh CLI
  - understanding the git-only PR submission path
  - debugging PR creation workflows
last_audited: "2026-02-05"
audit_result: edited
---

# PR Submission Workflow (Git-Only Path)

When creating PRs without Graphite (`gt`), use git + GitHub CLI (`gh pr create`). This is the simpler path for non-stacked PRs.

## When to Use Git-Only Path

- Not using Graphite stacking
- Simple feature branch workflow (branch directly from master)
- One-off PR creation

**Alternative:** For stacked PRs, use Graphite (`gt submit`).

## Workflow

1. `git checkout -b feature-name` — Create feature branch
2. Make changes and commit
3. `git push -u origin feature-name` — Push with upstream
4. `gh pr create --fill` or `gh pr create --title "..." --body "..."` — Create PR
5. `erk pr check` — Validate PR structure

## Comparison: Git-Only vs Graphite

| Feature       | Git-Only            | Graphite (`gt`)    |
| ------------- | ------------------- | ------------------ |
| Stacked PRs   | Manual branching    | Automatic stacking |
| PR submission | `gh pr create`      | `gt submit`        |
| Branch sync   | `git pull --rebase` | `gt sync`          |
| Complexity    | Simple              | More powerful      |

## Related Documentation

- [gh skill](../../.claude/skills/gh/SKILL.md) — GitHub CLI mental model and commands
- [Draft PR Handling](draft-pr-handling.md) — Draft PR workflows

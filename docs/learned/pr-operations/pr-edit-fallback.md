---
title: PR Edit Fallback Pattern
read_when:
  - "creating PRs from multi-session implementations"
  - "handling gh pr create failures"
  - "working with existing PRs"
---

# PR Edit Fallback Pattern

When `gh pr create` fails because a PR already exists, fall back to `gh pr edit`.

## Pattern

```bash
# Try create first
gh pr create --title "Title" --body "Body"

# If fails with "already exists", get PR number and edit
gh pr edit 7473 --title "Title" --body "Body"
```

## When This Happens

- Multi-part implementation sessions
- Resumed work on an existing branch
- Previous session created PR, current session wants to update

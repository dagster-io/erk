---
title: Plan Execution Patterns
read_when:
  - "implementing plans in worktrees"
  - "handling WIP commits during implementation"
---

# Plan Execution Patterns

## WIP Commit Handling

When changes are pre-committed as "WIP" (work in progress), agents should work with the existing commit structure rather than amending.

**Why**: The git safety protocol restricts commit --amend to specific scenarios:

1. User explicitly requested amend
2. Adding edits from pre-commit hook

**Anti-pattern**: Amending a WIP commit made by another process or earlier in the session without checking authorship.

**Correct pattern**: Treat WIP commits as valid starting points. Add new commits on top or create fixup commits if cleanup is needed later.

See git safety protocol in CLAUDE.md for complete rules.

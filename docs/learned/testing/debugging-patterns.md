---
title: Debugging Patterns
read_when:
  - "debugging test failures"
  - "recovering from bad state during development"
  - "using git stash during implementation"
---

# Debugging Patterns

## Git Stash for State Recovery

When implementation creates unrecoverable state, use git stash to temporarily save work, test against clean state, then re-apply:

```bash
# Save current work
git stash push -m "WIP: feature implementation"

# Test against clean state
make test

# Re-apply and continue
git stash pop
```

## Incremental Verification

When a change touches multiple files:

1. Save the full changeset to stash
2. Apply changes one file at a time
3. Run tests after each file to isolate breakage

This is faster than binary search through commits for recently introduced bugs.

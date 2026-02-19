---
title: Pre-Existing Test Failures Pattern
read_when:
  - "debugging test failures during refactoring"
  - "working in a codebase with known test failures"
  - "distinguishing new failures from old ones"
---

# Pre-Existing Test Failures Pattern

When working in a codebase with known test failures, use this pattern to distinguish pre-existing failures from new ones.

## The git stash Pattern

```bash
# Establish baseline (what fails without your changes)
git stash
pytest path/to/tests
# Note the failures

# Test your changes
git stash pop
pytest path/to/tests
# Compare failures - any new ones are yours to fix
```

## Why This Matters

During refactoring, seeing test failures can be confusing:

- Are these caused by my changes?
- Were they already broken?
- Am I wasting time debugging unrelated issues?

The stash pattern gives you clarity: if a test fails both before and after your changes, it's pre-existing.

## When to Use

- During large refactors that touch many files
- When entering an unfamiliar area of the codebase
- When test failures seem unrelated to your changes

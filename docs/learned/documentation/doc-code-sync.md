---
title: Documentation Co-Evolution During Refactoring
read_when:
  - "planning refactors that affect documentation"
  - "understanding doc maintenance during code changes"
  - "learning the co-evolution pattern"
---

# Documentation Co-Evolution

Update documentation alongside code changes, not after.

## The Pattern

During refactoring:

1. Identify affected docs (grep for terms being renamed)
2. Include doc updates in the same PR
3. Verify doc accuracy as part of implementation

## Benefits

- Docs stay accurate (never drift)
- Validates understanding (wrong doc = wrong mental model)
- Reduces future maintenance
- Single review for code + docs

## Anti-Pattern

"I'll update docs later" leads to:

- Forgotten updates
- Docs that drift silently
- Future agents re-learning solved problems

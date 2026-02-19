---
title: Documentation Bulk Update Pattern
read_when:
  - "updating documentation during renames"
  - "planning doc updates for large refactors"
  - "learning systematic doc maintenance approach"
---

# Documentation Bulk Update Pattern

When renaming code, update docs systematically.

## The Pattern

1. **Grep for references** across both `src/` and `docs/`
2. **Read all matching files** in parallel
3. **Edit systematically** by category:
   - Source code changes first
   - Test files second
   - Documentation third

## Why Co-Evolution Matters

Updating docs alongside code:

- Prevents drift (docs stay accurate)
- Reduces future maintenance burden
- Validates that you understand all impact areas
- Catches issues early (wrong doc = wrong understanding)

## Anti-Pattern

"I'll update docs later" leads to:

- Forgotten updates
- Docs that drift silently
- Future agents re-learning solved problems

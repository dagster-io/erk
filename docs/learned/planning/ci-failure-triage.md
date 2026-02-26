---
title: CI Failure Triage Pattern
read_when:
  - "CI fails during implementation"
  - "deciding whether to fix failing tests"
  - "triaging type checking errors"
---

# CI Failure Triage Pattern

## Step 1: Identify Error Location

Check if the failing code is in files modified by the current PR:

```bash
git diff --name-only HEAD~1  # Files changed in this PR
```

## Step 2: Classify the Error

**PR-introduced:** Error is in a file you modified -> Fix it

**Pre-existing:** Error is in unmodified files -> Document and proceed

## Step 3: Handle Pre-existing Errors

1. Note the error in PR description or commit message
2. Do NOT attempt to fix unrelated code in the same PR
3. Optionally create a follow-up issue for the pre-existing error

## Example

Type checking found errors in a provider module (unresolved attributes and unknown arguments from a previous refactor). These were pre-existing errors, not introduced by the current PR. Agent correctly documented and proceeded without fixing.

## Related Topics

- [Erk Architecture Patterns](../architecture/erk-architecture.md) - General architecture patterns

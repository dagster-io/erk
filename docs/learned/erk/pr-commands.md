---
title: "PR Checkout Footer Validation Pattern"
read_when:
  - Adding checkout footers to PR bodies
  - Implementing PR-related features that involve validation
  - Debugging `erk pr check` failures
  - Encountering validation errors related to PR body format
sources:
  - "[Impl 5d99bc36]"
---

# PR Checkout Footer Validation Pattern

## Overview

The `erk pr check` command validates PR bodies against exact pattern requirements, not semantic equivalents. This document covers the specific validation logic for checkout footers and how to debug validation failures.

## The Requirement

When a PR body includes a checkout footer, it must use the exact format:

```
erk pr checkout <number>
```

### What Fails Validation

These semantically equivalent commands will **fail** validation:

```bash
# FAILS - uses worktree command
erk wt from-pr 123

# FAILS - missing "pr" subcommand
erk checkout 123

# FAILS - different command structure
erk worktree checkout-pr 123
```

Even though `erk wt from-pr <number>` produces the same result as `erk pr checkout <number>`, the validation code requires the specific `erk pr checkout` pattern.

## Why This Matters

The validation is implemented via regex pattern matching in `erk_shared.gateway.pr.submit.has_checkout_footer_for_pr()`. The validator:

1. Searches the PR body for specific command patterns
2. Matches against literal text, not semantic meaning
3. Returns `True` only if the exact pattern is found

This is not a limitation but a design choice - PR bodies serve as user-facing documentation, and consistency in command format improves readability.

## Debugging Validation Failures

When `erk pr check` fails with a validation error:

1. **Read the error message** - it will indicate which validation failed
2. **Grep the codebase** for the validation function name (e.g., `has_checkout_footer_for_pr`)
3. **Read the source code** to understand the exact pattern requirement
4. **Update the PR body** to match the required pattern
5. **Re-run validation** to confirm the fix

### Example: Investigating Footer Validation

From session 5d99bc36, when `erk pr check` failed:

```bash
# Step 1: Error message indicated footer validation failed
$ erk pr check
Error: PR body missing required checkout footer

# Step 2: Grep for the validation function
$ grep -r "has_checkout_footer" src/
src/erk_shared/gateway/pr/submit.py: def has_checkout_footer_for_pr(body: str, pr_number: int) -> bool:

# Step 3: Read the source to find the exact pattern
# Discovered: Must be exactly "erk pr checkout <number>"

# Step 4: Update PR body with correct format
$ gh pr edit --body "... footer updated with erk pr checkout 123"

# Step 5: Verify
$ erk pr check
✓ All checks passed
```

## Source Code Reference

The validation logic is implemented in:

- **Location**: `erk_shared.gateway.pr.submit.has_checkout_footer_for_pr()`
- **Pattern**: Searches for `erk pr checkout <number>` in PR body text
- **Returns**: Boolean indicating whether the exact pattern was found

## Best Practices

1. **Don't guess at patterns** - read the validation source code when failures occur
2. **Use exact command format** - `erk pr checkout` not semantic equivalents
3. **Test validation iteratively** - update, run `erk pr check`, repeat if needed
4. **Document command patterns** - if creating new validators, document the exact pattern required

## Related Documentation

- [PR Body Validation Workflow](../planning/pr-submission-patterns.md) - Iterate-until-valid pattern for PR updates
- [Source Code Investigation Pattern](../planning/debugging-patterns.md) - General debugging approach for validation failures

## Summary

When adding checkout footers to PR bodies:

- Use exact format: `erk pr checkout <number>`
- Don't rely on semantic equivalents like `erk wt from-pr <number>`
- Debug validation failures by reading source code, not trial-and-error
- The validator checks pattern matching, not functional equivalence

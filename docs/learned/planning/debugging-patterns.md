---
title: "Source Code Investigation Pattern for Debugging"
read_when:
  - Debugging validation failures
  - Encountering errors with unclear root causes
  - Deciding whether to guess at fixes or investigate source
  - Working with error messages that reference specific functions
sources:
  - "[Impl 5d99bc36]"
---

# Source Code Investigation Pattern for Debugging

## Overview

When debugging validation failures or errors with unclear requirements, reading source code is often faster and more reliable than trial-and-error. This document covers the pattern for investigating error root causes through source code.

## The Pattern

```bash
# 1. Get error message
$ erk pr check
Error: Missing required checkout footer for PR #123

# 2. Extract key terms from error
# "checkout footer" -> search terms: "checkout_footer", "has_checkout", "footer"

# 3. Grep codebase for validation function
$ grep -r "checkout_footer" src/
src/erk_shared/gateway/pr/submit.py: def has_checkout_footer_for_pr(...)

# 4. Read the validation source
$ cat src/erk_shared/gateway/pr/submit.py
# Find has_checkout_footer_for_pr() function
# Discover pattern requirement: r"erk pr checkout \d+"

# 5. Apply fix based on source understanding
$ gh pr edit --body "...

---
erk pr checkout 123"

# 6. Verify fix
$ erk pr check
✓ All checks passed
```

## When to Use This Pattern

### Use source investigation when:

1. **Error message is unclear** about exact requirements
   - Example: "Invalid format" without showing what format is expected

2. **Multiple attempts fail** despite reasonable fixes
   - Example: Trying "erk checkout", "erk wt from-pr", both fail

3. **Pattern requirements seem non-obvious**
   - Example: "Must include checkout footer" but unclear what format is valid

4. **Validation involves regex or complex parsing**
   - Example: Errors mentioning "pattern match failed"

5. **Documentation doesn't exist or is incomplete**
   - Example: New validation rule not yet documented

### Don't use source investigation when:

1. **Error message is crystal clear** about the fix
   - Example: "Missing required field 'title'" → just add title field

2. **Pattern is obvious** from context
   - Example: "Email must be valid format" → use standard email format

3. **One attempt succeeds** - no need to investigate further

## Why This Approach Works

### Speed Comparison

**Trial-and-error approach** (from session 5d99bc36):

- Attempt 1: `erk checkout 123` → fails (2 min)
- Attempt 2: `erk wt from-pr 123` → fails (2 min)
- Attempt 3: `erk pr checkout 123` → works (2 min)
- **Total: 6 minutes**

**Source investigation approach**:

- Grep for function (10 sec)
- Read source code (1 min)
- Apply correct fix (30 sec)
- **Total: ~2 minutes**

### Accuracy

- **Trial-and-error**: May still guess wrong pattern
- **Source investigation**: Guarantees correct pattern understanding

## Real-World Example

### Problem: PR Validation Failing

From session 5d99bc36, debugging checkout footer validation:

```bash
# Initial error
$ erk pr check
Error: Missing required checkout footer for PR #123
```

### Investigation Process

```bash
# Step 1: Grep for validation function
$ grep -r "has_checkout_footer" src/
src/erk_shared/gateway/pr/submit.py: def has_checkout_footer_for_pr(body: str, pr_number: int) -> bool:

# Step 2: Read the source
$ cat src/erk_shared/gateway/pr/submit.py
```

Source code revealed:

```python
def has_checkout_footer_for_pr(body: str, pr_number: int) -> bool:
    """Check if PR body contains checkout footer for this PR."""
    pattern = rf"erk pr checkout {pr_number}"
    return bool(re.search(pattern, body))
```

**Key insight**: Must be exactly `erk pr checkout <number>`, not semantic equivalents.

### Fix Application

```bash
# Update PR body with exact pattern
$ gh pr edit --body "## Summary
Fix authentication bug

## Test Plan
- [x] Manual testing

---
erk pr checkout 123"

# Verify immediately
$ erk pr check
✓ All checks passed
```

**Result**: First attempt succeeds because pattern was understood correctly from source.

## Common Investigation Targets

### Validation Functions

Pattern: Functions named `validate_*`, `check_*`, `has_*`, `is_valid_*`

```bash
# Search patterns
grep -r "def validate_" src/
grep -r "def check_" src/
grep -r "def has_.*footer" src/
```

### Regex Patterns

Pattern: Look for `re.match()`, `re.search()`, `re.compile()` calls

```python
# What to look for in source
pattern = r"exact regex pattern here"
if re.search(pattern, input_text):
    # Validation passes
```

The regex pattern tells you exactly what format is required.

### Error Message Origins

Pattern: Grep for the exact error message text

```bash
# If error is "Missing required checkout footer"
grep -r "Missing required checkout footer" src/
# Find where error is raised, read surrounding validation logic
```

## Best Practices

1. **Start with error message** - extract key terms for grepping
2. **Grep broadly first** - use short search terms to find candidates
3. **Read surrounding context** - don't just read the function, read its usage
4. **Understand the why** - regex patterns reveal intent, not just requirements
5. **Document for next time** - if investigation was needed, the pattern may be non-obvious

## Integration with Iterate-Until-Valid

Source investigation complements the iterate-until-valid pattern:

1. **First validation failure**: Try obvious fix
2. **Second validation failure**: Investigate source
3. **Third attempt**: Apply fix based on source understanding
4. **Success**: Pattern is now understood and documented

Don't wait until 5-6 failures to investigate source. After 2 failed attempts, invest time in understanding the requirement correctly.

## Related Documentation

- [PR Body Validation Workflow](pr-submission-patterns.md) - Iterate-until-valid pattern
- [PR Checkout Footer Validation](../erk/pr-commands.md) - Specific validation example

## Summary

When debugging validation failures:

1. **Extract key terms** from error message
2. **Grep codebase** for validation functions
3. **Read source code** to understand exact requirements
4. **Apply fix** based on source understanding
5. **Verify immediately** to confirm fix is correct

**Time investment**: 2 minutes of source investigation saves 10+ minutes of trial-and-error.

**Accuracy**: Guarantees correct understanding vs. guessing at patterns.

**When to use**: After 1-2 failed attempts, or when error message is unclear about requirements.

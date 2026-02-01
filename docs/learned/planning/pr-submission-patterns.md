---
title: PR Submission Patterns
read_when:
  - "creating PRs programmatically"
  - "implementing idempotent PR submission"
  - "handling retry logic for PR operations"
---

# PR Submission Patterns

Patterns for reliable, idempotent PR creation and submission.

## Idempotent PR Submission

PR submission operations should be idempotent: running them multiple times produces the same result as running once.

### The Problem

Without idempotency checks:

1. First run: Creates PR #123
2. Hook blocks → retry
3. Second run: Creates duplicate PR #124
4. Now have two PRs for same work

### The Solution: Existing PR Detection

Before creating a PR, check if one already exists for the branch:

```bash
# Check for existing PR by branch name
EXISTING_PR=$(gh pr list --head "$BRANCH_NAME" --json number -q '.[0].number' 2>/dev/null || echo "")

if [ -n "$EXISTING_PR" ]; then
  echo "PR #$EXISTING_PR already exists for branch $BRANCH_NAME"
  # Update existing PR instead of creating new one
  gh pr edit "$EXISTING_PR" --title "$TITLE" --body "$BODY"
else
  # Create new PR
  gh pr create --title "$TITLE" --body "$BODY"
fi
```

### Branch-Based Discovery

Use `--head` flag for branch-based PR discovery:

| Method            | Reliability | Notes                      |
| ----------------- | ----------- | -------------------------- |
| `--head $BRANCH`  | High        | Exact match on branch name |
| Body text search  | Low         | Can match unrelated PRs    |
| PR number storage | Medium      | Requires persistent state  |

### Session-Scoped Idempotency

For session-aware operations (like plan-save), track created artifacts by session ID:

1. Check if artifact was created for this session ID
2. If found, return existing artifact
3. If not found, create and record

This prevents duplicate issues when retry loops occur.

## PR Body Generation

### Consistent Structure

PR bodies should follow a consistent structure:

```markdown
## Summary

[Brief description of changes]

## Plan

#123 <!-- Links to plan issue -->

## Changes

- Change 1
- Change 2

---

<!-- Footer with checkout instructions -->
```

### Checkout Footer Pattern

Include checkout instructions in a standard format:

```markdown
`gh pr checkout 456`
```

**Important:** Use plain text backtick format, not HTML `<details>` tags. The `has_checkout_footer_for_pr()` validation expects the backtick format.

### Closing Reference

Ensure PRs include issue closing keywords in the commit message (not just PR body):

- Commit message: `Implements feature X\n\nCloses #123`
- PR body: `**Plan:** #123` (for reference, not closing)

GitHub only auto-closes issues from merge commit messages, not PR bodies.

## Concurrent Submission Safety

When multiple submissions might occur simultaneously:

### Race Condition Avoidance

```bash
# Use atomic check-and-create pattern
# Note: This is pseudo-code - actual implementation may vary

# 1. Check for existing PR
PR_NUMBER=$(gh pr list --head "$BRANCH" --json number -q '.[0].number')

# 2. If not found, attempt creation
if [ -z "$PR_NUMBER" ]; then
  PR_NUMBER=$(gh pr create ... --json number -q '.number')
fi

# 3. Use PR_NUMBER for all subsequent operations
gh pr edit "$PR_NUMBER" ...
```

### Retry Strategy

For operations that might fail transiently:

1. **Check existing first**: Always check for existing artifact before creating
2. **Create if missing**: Only create when check confirms nothing exists
3. **Update on conflict**: If creation fails due to conflict, fall back to update

## PR Body Validation Workflow (Iterate-Until-Valid Pattern)

When creating or updating PRs in erk, validation failures often require an iterative approach.

### The Pattern

```bash
# 1. Update PR body with required fields
gh pr edit --body "..."

# 2. Run validation
erk pr check

# 3. Read error message
# Error: Missing required checkout footer

# 4. Investigate source code (if pattern is unclear)
grep -r "has_checkout_footer" src/

# 5. Update PR body with fix
gh pr edit --body "... with correct footer format"

# 6. Re-validate
erk pr check

# Repeat steps 2-6 until validation passes
```

### When to Use

Use iterate-until-valid when:

1. **Initial PR creation** - ensuring all required fields are present
2. **Validation failures** - fixing specific validation errors
3. **Pattern requirements unclear** - discovering exact format through iteration
4. **Complex validation logic** - multiple validators must pass

### Two-Phase PR Update Strategy

**Phase 1: Add Required Fields**

Start with the known requirements:

```bash
# Add title, summary, checkout footer
gh pr edit \
  --title "Fix authentication bug" \
  --body "## Summary
Fix token refresh logic

## Test Plan
- [ ] Manual testing with expired token
- [ ] Unit tests for refresh flow

---
erk pr checkout 123"
```

**Phase 2: Validate and Iterate**

Run validation and fix errors iteratively:

```bash
# First validation attempt
$ erk pr check
Error: Test plan incomplete - missing checked items

# Fix: Add at least one checked item
$ gh pr edit --body "...
- [x] Manual testing with expired token
- [ ] Unit tests for refresh flow
..."

# Second validation attempt
$ erk pr check
✓ All checks passed
```

### When to Read Source Code

**Read source code when:**

- Error message is unclear about the exact requirement
- Multiple attempts with reasonable fixes still fail
- Pattern requirements seem inconsistent with intuition
- Validation logic involves regex or complex parsing

**Example from session 5d99bc36:**

The error "Missing checkout footer" was clear, but the exact pattern requirement was not obvious. Instead of trial-and-error:

```bash
$ grep -r "has_checkout_footer" src/
# Read erk_shared.gateway.pr.submit.has_checkout_footer_for_pr()
# Discover exact pattern: "erk pr checkout <number>"
# Fix immediately
```

### Best Practices

1. **Start with known requirements** - add obvious fields first (title, summary, footer)
2. **Run validation early** - don't wait until PR submission to discover issues
3. **Read errors carefully** - messages often indicate exactly what's missing
4. **Investigate source when stuck** - grep codebase for validator function names
5. **Iterate quickly** - update, validate, fix, repeat until passing
6. **Document patterns** - if validation logic is non-obvious, document it

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Full plan lifecycle including PR creation
- [Submit Branch Reuse](submit-branch-reuse.md) - Branch reuse detection in plan submit
- [PR Checkout Footer Validation Pattern](../erk/pr-commands.md) - Specific validation details for checkout footers
- [Source Code Investigation Pattern](debugging-patterns.md) - General debugging approach for validation failures

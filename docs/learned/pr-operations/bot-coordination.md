---
title: Bot Coordination in PR Reviews
read_when:
  - handling multiple automated code review comments
  - resolving overlapping bot feedback
  - coordinating responses across review bots
tripwires: []
---

# Bot Coordination in PR Reviews

## The Problem

Multiple automated bots may analyze the same code during PR review:

- **Dignified Python Review**: Python standards compliance
- **Code Simplifier**: Refactoring suggestions
- **Tripwire Checker**: Critical pattern violations
- **Future bots**: Additional analyzers as the system evolves

These bots may flag the same code location with different perspectives, leading to overlapping or redundant feedback.

## The Pattern

When you receive multiple bot comments on a PR:

1. **Read ALL comments first** - Don't act on the first comment immediately
2. **Identify overlaps** - Note which comments reference the same code location
3. **Synthesize perspectives** - Multiple viewpoints may inform a single resolution
4. **Find the root issue** - Sometimes overlapping feedback points to a deeper problem
5. **Respond to EACH comment** - Even if the fix addresses multiple concerns

## Real Example

**Code location**: `src/erk/main.py:15`

**Bot 1 (Code Simplifier)**: "This debug print statement should be removed"
**Bot 2 (Dignified Python)**: "Use `click.echo()` instead of `print()` for CLI output"
**Bot 3 (Tripwires)**: "CLI output must use Click framework for proper encoding"

**Analysis**: All three bots identified the same issue from different angles:

- Code Simplifier thought it was debug code
- Dignified Python flagged the wrong output method
- Tripwires highlighted the architectural requirement

**Resolution**:

1. Check `.impl/plan.md` - the print statement was the planned feature
2. Code is correct (uses `click.echo()` already)
3. Respond to each bot explaining the false positive context

## Coordination Strategies

### Strategy 1: Address Root Cause

When multiple bots flag the same location, look for the underlying issue:

```
Bot A: "Variable name unclear"
Bot B: "Function too complex"
Bot C: "Missing type annotation"

Root cause: Function needs refactoring
Resolution: Refactor function → fixes all three concerns
```

### Strategy 2: Distinguish Valid from Invalid

Not all bot feedback is correct. Prioritize based on plan intent:

```
Bot A: "Remove this feature" (contradicts plan)
Bot B: "Add error handling" (valid improvement)

Resolution:
- Dismiss Bot A with plan context explanation
- Address Bot B's valid concern
```

### Strategy 3: Batch Responses

When making a single fix that addresses multiple comments:

```
Fixed in commit abc123:
- Addressed feedback from Bot A (see comment thread)
- Resolved Bot B's concern about X
- Implemented Bot C's suggestion for Y
```

## Future Improvements

Potential enhancements to bot coordination:

1. **Pre-submission deduplication**: Aggregate bot feedback before posting
2. **Priority ranking**: Critical issues first, suggestions later
3. **Cross-bot context**: Bots aware of each other's feedback
4. **Unified response threads**: Group related feedback

These are architectural improvements, not immediate action items.

## When to Escalate

If bot feedback is:

- **Contradictory with plan**: Use `AskUserQuestion` (see [Handling Contradictory Feedback](../review/handling-contradictory-feedback.md))
- **Unclear or ambiguous**: Request clarification from user
- **Overlapping extensively**: Consider if bot configuration needs adjustment

## Related Documentation

- [Handling Contradictory Feedback](../review/handling-contradictory-feedback.md) - False positive detection
- [PR Validation Rules](pr-validation-rules.md) - Automated validation checks

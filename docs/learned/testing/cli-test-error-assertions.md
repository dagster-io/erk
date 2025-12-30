---
title: CLI Test Error Message Assertion Patterns
read_when:
  - "writing CLI tests with error assertions"
  - "testing error messages in Click commands"
  - "asserting on CLI output"
---

# CLI Test Error Message Assertion Patterns

**Pattern**: Assert on semantic keywords rather than exact error message text.

## Problem

CLI error messages change over time: phrasing improves, details are added, punctuation changes. Tests that assert on exact message text become brittle and fail when messages are refined.

## Solution

Assert on semantic keywords that identify the error type, not exact phrasing:

```python
# CORRECT: Assert on semantic keywords that indicate the error type
assert result.exit_code != 0
assert "not authenticated" in result.output  # Key concept

# CORRECT: Multiple keywords for specificity without brittleness
assert result.exit_code != 0
assert "commits" in result.output and "ahead" in result.output

# WRONG: Exact message match - breaks when wording changes
assert result.output == "Error: No commits found. Cannot submit.\n"

# WRONG: Too specific - breaks on punctuation or formatting changes
assert "No commits found." in result.output  # Period may change to colon
```

## Keyword Selection Guidelines

Choose assertion keywords that:

1. **Identify the error type**: "authenticated", "not found", "ahead", "permission"
2. **Are unlikely to change**: Core nouns over connecting words
3. **Distinguish from other errors**: "commits ahead" vs just "commits"

## Exit Code + Message Pattern

Always assert exit code alongside message content:

```python
# CORRECT: Exit code validates failure, message validates reason
assert result.exit_code != 0
assert "not authenticated" in result.output

# INCOMPLETE: Message without exit code
assert "not authenticated" in result.output  # Command might still succeed!
```

## Anti-Pattern: Exact Error Message Assertions

```python
# WRONG: Exact message match - extremely brittle
def test_fails_when_branch_empty() -> None:
    result = runner.invoke(command, obj=ctx)
    assert result.exit_code != 0
    assert result.output == "Error: No commits found. Cannot submit.\n"
    # Breaks when: message changes to "No commits ahead of main. Nothing to submit."

# WRONG: Too specific - breaks on punctuation or formatting changes
def test_unauthenticated_error() -> None:
    result = runner.invoke(command, obj=ctx)
    assert "Error: Not authenticated." in result.output
    # Breaks when: period changes to colon, or "Error:" prefix removed
```

### Why Exact Matching Is Wrong

**Problems with exact message assertions**:

- **Brittle**: Break when error messages are improved or refined
- **False failures**: Tests fail even though behavior is correct
- **Maintenance burden**: Every message change requires updating tests
- **Wrong focus**: Tests implementation detail (message text) not behavior (error type)

**Error message wording is an implementation detail**. Tests should verify the **type** of error (authentication failed, resource not found, validation error), not its exact phrasing.

## When to Use Exact Matches

Use exact matching only when:

- Testing specific formatting (e.g., JSON output, table columns)
- Message is contractual API (e.g., machine-parseable status codes)
- Testing message composition logic itself

For typical error messages, prefer keyword assertions.

## Benefits

- **Resilience**: Tests survive message improvements
- **Maintenance**: Less test churn when messages evolve
- **Intent**: Keywords document what makes the error unique
- **Coverage**: Still validates correct error was raised

---
title: Step Extraction Format
read_when:
  - "creating plans with extractable steps"
  - "writing test fixtures with impl folders"
  - "debugging empty steps in progress.md"
tripwires:
  - action: "creating test plan content without ## Step N: format"
    warning: "Use '## Step N: Title' format. Regex extraction pattern is `^## Step \\d+[:\\s]+(.+)$`. Other formats (1. Step, - Step) will result in empty steps array."
---

# Step Extraction Format

Implementation plans must use a specific format for steps to be extracted into `progress.md`.

## The Extraction Pattern

Steps are extracted using this regex pattern:

```
^## Step \d+[:\s]+(.+)$
```

This matches:

- Line starts with `## Step`
- Followed by one or more digits
- Followed by `:` or whitespace
- Captures the title (everything after)

## Valid Formats

```markdown
## Step 1: Database Schema

## Step 2: API Endpoints

## Step 3: Integration Tests
```

or without colon:

```markdown
## Step 1 Database Schema

## Step 2 API Endpoints

## Step 3 Integration Tests
```

## Invalid Formats

These formats will NOT be extracted:

```markdown
# Step 1: Title # Wrong: Uses # instead of

### Step 1: Title # Wrong: Uses ### instead of

1. First step # Wrong: Numbered list format

- First step # Wrong: Bullet list format
  Step 1: Title # Wrong: Missing ## prefix

## 1. Title # Wrong: Missing "Step" keyword
```

## Example: Complete Plan

```markdown
# Implementation Plan

## Overview

This plan implements the user authentication feature.

## Step 1: Database Schema

Create the users table with the following columns:

- id (UUID primary key)
- email (unique)
- password_hash

## Step 2: API Endpoints

Implement REST endpoints:

- POST /auth/register
- POST /auth/login
- POST /auth/logout

## Step 3: Integration Tests

Write tests covering:

- Registration flow
- Login/logout flow
- Invalid credentials handling

## Success Criteria

All tests pass with 80% coverage.
```

This extracts to: `["Database Schema", "API Endpoints", "Integration Tests"]`

## Creating Test Fixtures

When writing tests that use `create_impl_folder()`, ensure your plan content uses the correct format:

```python
# CORRECT: Uses ## Step N: format
plan_content = """# Test Plan

## Step 1: First step

Do the first step.

## Step 2: Second step

Do the second step.
"""
create_impl_folder(tmp_path, plan_content, prompt_executor=None, overwrite=False)

# Resulting progress.md has 2 steps
```

```python
# WRONG: Uses numbered list format (will result in 0 steps!)
plan_content = """# Test Plan

1. First step
2. Second step
"""
create_impl_folder(tmp_path, plan_content, prompt_executor=None, overwrite=False)

# Resulting progress.md has 0 steps - regex doesn't match!
```

## Why This Format?

The regex-based extraction replaced an earlier LLM-based approach for determinism:

1. **Deterministic**: Same input always produces same output
2. **Fast**: No LLM API calls needed
3. **Predictable**: Easy to understand what will be extracted
4. **Testable**: Can verify extraction in unit tests

## Implementation Details

The extraction function is `extract_steps_from_plan_regex()` in `erk_shared.impl_folder`:

```python
def extract_steps_from_plan_regex(plan_content: str) -> list[str]:
    """Extract step headers from plan markdown using regex."""
    pattern = r"^## Step \d+[:\s]+(.+)$"
    matches = re.findall(pattern, plan_content, re.MULTILINE)
    return [match.strip() for match in matches]
```

## Related Documentation

- [Progress Schema Reference](progress-schema.md) - The resulting progress.md structure
- [Plan Schema Reference](plan-schema.md) - GitHub issue plan structure

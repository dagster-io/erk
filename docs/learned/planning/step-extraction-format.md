---
title: Step Extraction Format
read_when:
  - "creating plans with extractable steps"
  - "writing test fixtures with impl folders"
  - "debugging empty steps in progress.md"
tripwires:
  - action: "creating test plan content without frontmatter steps"
    warning: "Plans MUST have steps for tracking. Either add a `steps:` array in YAML frontmatter with dictionaries containing 'name' keys, or use the --steps CLI option when saving."
---

# Step Extraction Format

Implementation plans must include a `steps:` array in YAML frontmatter for step tracking to work.

## Primary Format: YAML Frontmatter Steps (Required)

Plans saved via `/erk:plan-save` **must** include steps in YAML frontmatter. Each step must be a dictionary with a `name` key:

```markdown
---
steps:
  - name: "Create database schema"
  - name: "Implement API endpoints"
  - name: "Add integration tests"
---

# Implementation Plan

## Overview

This plan implements the user authentication feature.

## Step 1: Create database schema

Details here...
```

The frontmatter `steps:` array is the **authoritative source** for step tracking.

## Why Dictionaries?

Using `- name: "..."` instead of plain strings makes the schema extensible. Future fields can be added without breaking existing plans:

```yaml
steps:
  - name: "Create database schema"
    estimate: "small"
  - name: "Implement API endpoints"
    depends_on: 1
```

## Validation at Save Time

The `plan-save-to-issue` command validates frontmatter before saving:

- **Missing `steps:` key** → Error with instructions to add frontmatter
- **`steps:` not a list** → Error with type mismatch message
- **Empty `steps: []`** → Error requiring at least one step
- **Step not a dict** → Error with format instructions
- **Step missing `name`** → Error with format instructions

This ensures all plans have valid step tracking from the start.

### Alternative: CLI --steps Option

Instead of adding steps to frontmatter, you can provide steps via the CLI:

```bash
erk exec plan-save-to-issue --steps "First step" --steps "Second step" --format display
```

The `--steps` option injects steps into the plan frontmatter at save time, overriding any existing steps. This is useful when you don't want to modify the plan file.

## Fallback: Regex Extraction (Backwards Compatibility)

For plans without frontmatter, regex extraction is used as a fallback:

```
^## Step \d+[:\s]+(.+)$
```

This matches:

- Line starts with `## Step`
- Followed by one or more digits
- Followed by `:` or whitespace
- Captures the title (everything after)

### Regex-Compatible Headers

```markdown
## Step 1: Database Schema

## Step 2: API Endpoints

## Step 3: Integration Tests
```

**Note**: Frontmatter steps take precedence. If both exist, frontmatter is used.

## Creating Test Fixtures

When writing tests, use frontmatter steps for reliability:

```python
# CORRECT: Uses frontmatter steps with name key (preferred)
plan_content = """---
steps:
  - name: "First step"
  - name: "Second step"
---

# Test Plan

Content here...
"""
create_impl_folder(tmp_path, plan_content, prompt_executor=None, overwrite=False)

# Resulting progress.md has 2 steps from frontmatter
```

Or use regex format if testing backwards compatibility:

```python
# CORRECT: Uses ## Step N: format (fallback)
plan_content = """# Test Plan

## Step 1: First step

Do the first step.

## Step 2: Second step

Do the second step.
"""
create_impl_folder(tmp_path, plan_content, prompt_executor=None, overwrite=False)

# Resulting progress.md has 2 steps from regex extraction
```

## Invalid Formats

These formats will NOT be extracted (no frontmatter, no valid headers):

```markdown
# Step 1: Title # Wrong: Uses # instead of

### Step 1: Title # Wrong: Uses ### instead of

1. First step # Wrong: Numbered list format

- First step # Wrong: Bullet list format

## 1. Title # Wrong: Missing "Step" keyword
```

## Implementation Details

Steps are extracted using `extract_steps_from_plan_with_fallback()`:

```python
def extract_steps_from_plan_with_fallback(plan_content: str) -> list[str]:
    """Extract steps from plan frontmatter, with regex fallback."""
    # Frontmatter is authoritative if present
    frontmatter_steps = extract_steps_from_frontmatter(plan_content)
    if frontmatter_steps is not None:
        return frontmatter_steps

    # Fallback to regex for backwards compatibility
    return extract_steps_from_plan_regex(plan_content)
```

## Why Frontmatter?

1. **Reliable**: Agent explicitly lists steps, no parsing ambiguity
2. **Validated**: Errors at save time, not implementation time
3. **Flexible**: Step titles don't need to match header format
4. **Extensible**: Dictionary format allows future metadata fields
5. **Simple**: No regex knowledge required for agents

## Related Documentation

- [Progress Schema Reference](progress-schema.md) - The resulting progress.md structure
- [Plan Schema Reference](plan-schema.md) - GitHub issue plan structure

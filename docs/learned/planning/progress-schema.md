---
title: Progress Schema Reference
read_when:
  - "understanding progress.md structure"
  - "debugging progress validation errors"
  - "creating test fixtures with progress.md"
  - "working with step tracking"
---

# Progress Schema Reference

Complete reference for the `.impl/progress.md` file structure used to track implementation progress.

## Overview

The `progress.md` file tracks step completion status for implementation plans. It uses YAML frontmatter as the source of truth, with markdown checkboxes for human readability.

## Schema

```yaml
---
current_step: 0          # Highest completed step number (0 = not started)
completed_steps: 0       # Count of completed steps
total_steps: 3           # Total number of steps
steps:                   # Array of step objects
  - number: 1
    title: "First step"
    completed: false
  - number: 2
    title: "Second step"
    completed: false
  - number: 3
    title: "Third step"
    completed: false
---

# Progress Tracking

- [ ] First step
- [ ] Second step
- [ ] Third step
```

## Field Reference

### Top-Level Fields

| Field             | Type | Description                                     |
| ----------------- | ---- | ----------------------------------------------- |
| `current_step`    | int  | Highest completed step number (0 = not started) |
| `completed_steps` | int  | Count of steps with `completed: true`           |
| `total_steps`     | int  | Total number of steps (must match array length) |
| `steps`           | list | Array of step objects                           |

### Step Object Fields

| Field       | Type | Description                         |
| ----------- | ---- | ----------------------------------- |
| `number`    | int  | 1-indexed step number               |
| `title`     | str  | Step title (extracted from plan)    |
| `completed` | bool | Whether the step has been completed |

### Key Distinction: current_step vs completed_steps

- **`completed_steps`**: Count of how many steps are done (e.g., 3 out of 5)
- **`current_step`**: The highest step number that's completed (progression marker)

Example: If steps 1 and 3 are completed (but not 2):

- `completed_steps: 2` (two steps done)
- `current_step: 3` (step 3 is the highest completed)

## Validation Rules

The `validate_progress_schema()` function checks:

1. **Required fields**: `steps`, `total_steps`, `completed_steps`, `current_step` must exist
2. **Type validation**: `steps` must be a list
3. **Step structure**: Each step must have `number` (int), `title`, and `completed`
4. **Count consistency**: `total_steps` must equal `len(steps)`
5. **Completed count**: `completed_steps` must match actual completed count
6. **Current step bounds**: `current_step` must be 0 <= n <= total_steps

## Example: Valid Progress File

```yaml
---
current_step: 2
completed_steps: 2
total_steps: 3
steps:
  - number: 1
    title: "Set up database schema"
    completed: true
  - number: 2
    title: "Implement API endpoints"
    completed: true
  - number: 3
    title: "Add integration tests"
    completed: false
---

# Progress Tracking

- [x] Set up database schema
- [x] Implement API endpoints
- [ ] Add integration tests
```

## Creating Progress Files in Tests

Use `create_impl_folder()` to generate valid progress files:

```python
from erk_shared.impl_folder import create_impl_folder

plan_content = """# Implementation Plan

## Step 1: First task

Details here.

## Step 2: Second task

More details.
"""

create_impl_folder(tmp_path, plan_content, prompt_executor=None, overwrite=False)
```

**Important**: The plan must use `## Step N: Title` format for regex extraction. See [Step Extraction Format](step-extraction-format.md).

## Python API

Key functions in `erk_shared.impl_folder`:

```python
# Validate progress schema
from erk_shared.impl_folder import validate_progress_schema
errors = validate_progress_schema(progress_file)  # Returns list[str]

# Parse frontmatter
from erk_shared.impl_folder import parse_progress_frontmatter
metadata = parse_progress_frontmatter(content)  # Returns dict or None

# Generate progress content
from erk_shared.impl_folder import generate_progress_content
content = generate_progress_content(["Step 1", "Step 2"])
```

## Related Documentation

- [Step Extraction Format](step-extraction-format.md) - Plan format requirements for step extraction
- [Plan Schema Reference](plan-schema.md) - GitHub issue plan structure

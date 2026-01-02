---
description: Save the current session's plan to GitHub as an issue
---

# /erk:plan-save

Save the current session's plan to GitHub as an issue with session context.

## Issue Structure

The created issue has a specific structure:

- **Issue body**: Contains only the metadata header (schema version, timestamps, etc.)
- **First comment**: Contains the actual plan content

This separation keeps machine-readable metadata in the body while the human-readable plan is in the first comment.

## Agent Instructions

### Step 0: Ensure Plan Has Frontmatter Steps

Before saving, verify the plan file has a `steps:` array in YAML frontmatter. Each step must be a dictionary with a `name` key:

```markdown
---
steps:
  - name: "First implementation step"
  - name: "Second implementation step"
---

# Plan Title

...
```

If the plan is missing frontmatter steps:

1. Read the plan file
2. Extract the logical implementation steps from the content
3. Add them to YAML frontmatter at the top of the file using the `- name: "..."` format
4. Save the updated plan file

The frontmatter is required for step tracking during implementation.

### Step 1: Extract Session ID

Get the session ID from the `SESSION_CONTEXT` reminder in your conversation context.

### Step 2: Run Save Command

Run this command with the extracted session ID:

```bash
erk exec plan-save-to-issue --format display --session-id="<session-id-from-step-1>"
```

### Step 3: Display Results

On success, display the command output verbatim. Do not summarize, reorder, or rewrite the next steps.

On failure, display the error message and suggest:

- Checking that a plan exists (enter Plan mode and exit it first)
- Verifying GitHub CLI authentication (`gh auth status`)
- Checking network connectivity

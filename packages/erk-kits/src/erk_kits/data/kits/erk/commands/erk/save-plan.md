---
description: Save the current session's plan to GitHub as an issue
---

# /erk:save-plan

Save the current session's plan to GitHub as an issue with session context.

## Issue Structure

The created issue has a specific structure:

- **Issue body**: Contains only the metadata header (schema version, timestamps, etc.)
- **First comment**: Contains the actual plan content

This separation keeps machine-readable metadata in the body while the human-readable plan is in the first comment.

## Agent Instructions

### Step 1: Extract Session ID

Get the session ID from the `SESSION_CONTEXT` reminder in your conversation context.

### Step 2: Run Save Command

Run this command with the extracted session ID:

```bash
erk kit exec erk plan-save-to-issue --format display --session-id="<session-id-from-step-1>"
```

### Step 3: Display Results

On success, display the URL to the user along with the suggested next steps from the output.

On failure, display the error message and suggest:

- Checking that a plan exists (enter Plan mode and exit it first)
- Verifying GitHub CLI authentication (`gh auth status`)
- Checking network connectivity

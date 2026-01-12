---
description: Update an existing plan issue with the current session's plan
argument-hint: <issue-number>
---

# /local:plan-update

Update an existing GitHub plan issue with the current session's plan content.

## Usage

```bash
/local:plan-update 42
/local:plan-update https://github.com/owner/repo/issues/42
```

---

## Agent Instructions

### Step 1: Parse Issue Number

Extract the issue number from the argument:

- If numeric (e.g., `42`), use directly
- If URL (e.g., `https://github.com/owner/repo/issues/42`), extract the number from the path

If no argument provided, check `.impl/issue.json` for a linked issue number.

If still no issue number, ask the user for the issue number.

### Step 2: Extract Session ID

Get the session ID by reading the `session:` line from the `SESSION_CONTEXT` reminder in your conversation context (e.g., `session: a8e2cb1d-...`). This value is already visible - just copy it directly, no tools needed.

### Step 3: Run Update Command

```bash
erk exec plan-update-issue --issue-number <issue> --format display --session-id="<session-id>"
```

### Step 4: Display Results

On success, display the command output verbatim.

On failure, display the error and suggest:

- Checking that a plan exists (enter plan mode and exit it first)
- Verifying the issue number is correct (`gh issue view <number>`)
- Checking GitHub CLI authentication (`gh auth status`)

---

## Related

- `/erk:plan-save` - Create new plan issue (instead of updating)
- `/erk:replan` - Recreate an obsolete plan from scratch
- `erk-planning` skill - Complete plan management documentation

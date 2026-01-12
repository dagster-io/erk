---
description: Save the current session's plan to GitHub as an issue
argument-hint: "[--objective-issue=<number>]"
---

# /erk:plan-save

Save the current session's plan to GitHub as an issue with session context.

## Usage

```bash
/erk:plan-save                           # Standalone plan
/erk:plan-save --objective-issue=3679    # Plan linked to objective
```

When creating a plan from an objective (via `/erk:objective-next-plan`), the exit-plan-mode hook will automatically suggest the command with the correct `--objective-issue` flag.

## Issue Structure

The created issue has a specific structure:

- **Issue body**: Contains only the metadata header (schema version, timestamps, etc.)
- **First comment**: Contains the actual plan content

This separation keeps machine-readable metadata in the body while the human-readable plan is in the first comment.

## Agent Instructions

### Step 1: Parse Arguments

Check `$ARGUMENTS` for the `--objective-issue` flag:

```
If $ARGUMENTS contains "--objective-issue=<number>":
  - Extract the number
  - Store as OBJECTIVE_ISSUE variable
  - Set OBJECTIVE_FLAG to "--objective-issue=<number>"
Else:
  - Set OBJECTIVE_FLAG to empty string
```

### Step 2: Extract Session ID

Get the session ID by reading the `session:` line from the `SESSION_CONTEXT` reminder in your conversation context (e.g., `session: a8e2cb1d-...`). This value is already visible - just copy it directly, no tools needed.

### Step 3: Run Save Command

Run this command with the extracted session ID and optional objective flag:

```bash
erk exec plan-save-to-issue --format json --session-id="<session-id>" ${OBJECTIVE_FLAG}
```

Parse the JSON output to extract `issue_number` for verification in Step 4.

If the command fails, display the error and stop.

### Step 4: Verify Objective Link (if applicable)

**Only run this step if `--objective-issue` was provided in arguments.**

Verify the objective link was saved correctly:

```bash
erk exec get-plan-metadata <issue_number> objective_issue
```

Parse the JSON response:

- If `success: true` and `value` matches the expected objective number: verification passed
- If `success: false` or value doesn't match: verification failed

**On verification success:**

Display: `Verified objective link: #<objective-number>`

**On verification failure:**

Display error and remediation steps:

```
ERROR: Objective link verification failed
Expected objective: #<expected>
Actual: <actual-or-null>

The plan was saved but without the correct objective link.
Fix: Close issue #<issue_number> and re-run:
  /erk:plan-save --objective-issue=<expected>
```

Exit without creating the plan-saved marker. The session continues so the user can retry.

### Step 5: Display Results

On success, display:

```
Plan saved as issue #<issue_number>
URL: <issue_url>

Next steps:

View Issue: gh issue view <issue_number> --web

In Claude Code: /erk:plan-submit

OR exit Claude Code first, then run one of:
  Interactive: erk implement <issue_number>
  Dangerous Interactive: erk implement <issue_number> --dangerous
  Auto-Submit: erk implement <issue_number> --yolo
  Submit to Queue: erk plan submit <issue_number>
```

If objective was verified, also display: `Verified objective link: #<objective-number>`

On failure, display the error message and suggest:

- Checking that a plan exists (enter Plan mode and exit it first)
- Verifying GitHub CLI authentication (`gh auth status`)
- Checking network connectivity

## Session Tracking

After successfully saving a plan, the issue number is stored in a marker file that enables automatic plan updates in the same session.

**To read the saved issue number:**

```bash
erk exec marker read --session-id <session-id> plan-saved-issue
```

This returns the issue number (exit code 0) or exits with code 1 if no plan was saved in this session.

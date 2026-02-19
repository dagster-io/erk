---
description: Save the current session's plan to GitHub
argument-hint: "[--objective-issue=<number>] [--plan-type=learn]"
---

# /erk:plan-save

Save the current session's plan to GitHub with session context.

## Usage

```bash
/erk:plan-save                           # Standalone plan
/erk:plan-save --objective-issue=3679    # Plan linked to objective
/erk:plan-save --plan-type=learn         # Learn plan (erk-learn label)
```

When creating a plan from an objective (via `/erk:objective-plan`), the exit-plan-mode hook will automatically suggest the command with the correct `--objective-issue` flag.

## Plan Storage

The plan is saved using the configured backend:

- **Draft PR backend** (`PLAN_BACKEND = "draft_pr"`): Creates a branch, pushes a plan commit, and opens a draft PR. Plan content is in the PR body after the metadata separator.
- **Issue backend** (`PLAN_BACKEND = "github"`): Creates a GitHub issue. Metadata in the issue body, plan content in the first comment.

The JSON output contract is the same for both backends (`issue_number`, `issue_url`, `title`, `branch_name`, `plan_backend`).

## Agent Instructions

### Step 1: Parse Arguments

Check `$ARGUMENTS` for the `--objective-issue` and `--plan-type` flags:

```
If $ARGUMENTS contains "--objective-issue=<number>":
  - Extract the number
  - Store as OBJECTIVE_ISSUE variable
  - Set OBJECTIVE_FLAG to "--objective-issue=<number>"
Else:
  - Set OBJECTIVE_FLAG to empty string

If $ARGUMENTS contains "--plan-type=<type>":
  - Extract the type (standard or learn)
  - Store as PLAN_TYPE variable
  - Set PLAN_TYPE_FLAG to "--plan-type=<type>"
Else:
  - Set PLAN_TYPE_FLAG to empty string
```

### Step 2: Run Save Command

Run this command with the session ID and optional flags:

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" ${OBJECTIVE_FLAG} ${PLAN_TYPE_FLAG}
```

Parse the JSON output to extract `issue_number` for verification in Step 3.

If the command fails, display the error and stop.

### Step 3: Verify Objective Link (if applicable)

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
Fix: Close <"draft PR" if plan_backend=="draft_pr", else "issue"> #<issue_number> and re-run:
  /erk:plan-save --objective-issue=<expected>
```

Exit without creating the plan-saved marker. The session continues so the user can retry.

### Step 3.5: Update Objective Roadmap (if objective linked)

**Only run this step if `--objective-issue` was provided and verification passed.**

Update the objective's roadmap table to show that a plan has been created for this node:

1. **Read the roadmap node marker** to get the node ID:

```bash
step_id=$(erk exec marker read --session-id "${CLAUDE_SESSION_ID}" roadmap-step)
```

If the marker doesn't exist (command fails), skip this step - the plan wasn't created via `objective-plan`.

2. **Update the roadmap table** using the dedicated command:

```bash
erk exec update-objective-node <objective-issue> --node "$step_id" --plan "#<issue_number>"
```

This atomically fetches the issue body, finds the matching node row, updates the Plan cell, sets the Status cell to `in-progress`, and writes the updated body back.

3. **Report the update:**

Display: `Updated objective #<objective-issue> roadmap: node <step_id> → plan #<issue_number>`

**Error handling:** If the roadmap update fails, warn but continue - the plan was saved successfully, just the roadmap tracking didn't update. The user can manually update the objective.

### Step 4: Display Results

On success, display based on `plan_backend` from JSON output:

**Header (both backends):**

```
Plan "<title>" saved as <"draft PR" if plan_backend=="draft_pr", else "issue"> #<issue_number>
URL: <issue_url>
```

**If `plan_backend` is `"draft_pr"`:**

```
Next steps:

View PR: gh pr view <issue_number> --web

In Claude Code:
  Submit to queue: /erk:plan-submit — Submit for remote agent implementation

Outside Claude Code:
  Local: erk br co <issue_number> && erk implement --dangerous
  Submit to queue: erk plan submit <issue_number>
```

**If `plan_backend` is `"github"` (or absent):**

```
Next steps:

View Issue: gh issue view <issue_number> --web

In Claude Code:
  Submit to queue: /erk:plan-submit — Submit plan for remote agent implementation
  Plan review: /erk:plan-review — Submit plan as PR for human review before implementation

OR exit Claude Code first, then run one of:
  Local: erk prepare <issue_number>
  Prepare+Implement: source "$(erk prepare <issue_number> --script)" && erk implement --dangerous
  Submit to Queue: erk plan submit <issue_number>
```

If objective was verified, also display: `Verified objective link: #<objective-number>`

If the JSON output contains `slot_name` and `slot_objective_updated: true`, also display: `Slot objective updated: <slot_name> → #<objective-number>`

**Note:** Slot objective updates are handled automatically by `plan-save` when `--objective-issue` is provided - no separate command call needed.

On failure, display the error message and suggest:

- Checking that a plan exists (enter Plan mode and exit it first)
- Verifying GitHub CLI authentication (`gh auth status`)
- Checking network connectivity

## Session Tracking

After successfully saving a plan, the issue number is stored in a marker file that enables automatic plan updates in the same session.

**To read the saved issue number:**

```bash
erk exec marker read --session-id "${CLAUDE_SESSION_ID}" plan-saved-issue
```

This returns the issue number (exit code 0) or exits with code 1 if no plan was saved in this session.

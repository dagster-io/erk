---
description: Save the current session's plan to GitHub
argument-hint: "[--plan-type=learn]"
---

# /erk:plan-save

Save the current session's plan to GitHub with session context.

## Usage

```bash
/erk:plan-save                           # Standalone plan
/erk:plan-save --plan-type=learn         # Learn plan (erk-learn label)
/erk:plan-save --objective=123           # Explicit objective link (overrides marker)
```

Objective linking: if a plan was created via `/erk:objective-plan`, the session's objective-context marker is read automatically by the save command. Use `--objective=<number>` to override the marker or provide the link when no marker exists (e.g., during replan).

## Plan Storage

The plan is saved using the configured backend:

- **Draft PR backend** (`PLAN_BACKEND = "draft_pr"`): Creates a branch, pushes a plan commit, and opens a draft PR. Plan content is in the PR body after the metadata separator.
  The JSON output contract includes `plan_number`, `plan_url`, `title`, `branch_name`, `plan_backend`.

## Agent Instructions

### Step 1: Parse Arguments

Check `$ARGUMENTS` for the `--plan-type` and `--objective` flags:

```
If $ARGUMENTS contains "--plan-type=<type>":
  - Extract the type (standard or learn)
  - Store as PLAN_TYPE variable
  - Set PLAN_TYPE_FLAG to "--plan-type=<type>"
Else:
  - Set PLAN_TYPE_FLAG to empty string

If $ARGUMENTS contains "--objective=<number>":
  - Extract the number
  - Set OBJECTIVE_FLAG to "--objective=<number>"
Else:
  - Set OBJECTIVE_FLAG to empty string
```

### Step 1.5: Generate Branch Slug

Before saving, generate a branch slug from the plan title. Read the plan title from the plan file you wrote in plan mode (the first `# ` heading).

Generate a branch slug from the title:

- 2-4 hyphenated lowercase words, max 30 characters
- Capture distinctive essence, drop filler words (the, a, for, implementation, plan)
- Prefer action verbs: add, fix, refactor, update, consolidate, extract, migrate
- Examples: "fix-auth-session", "add-plan-validation", "refactor-gateway-abc"

Store the result as `BRANCH_SLUG`.

### Step 1.75: Generate Plan Summary

Write a concise 2-3 sentence summary of the plan. This summary will be visible
at the top of the PR description (above the collapsed full plan).

Guidelines:

- Focus on WHAT the plan does and WHY
- Do not repeat the title
- Plain text, no markdown headers or formatting
- Avoid special shell characters (backticks, dollar signs)
- Store as PLAN_SUMMARY

### Step 2: Run Save Command

Run this command with the session ID, branch slug, summary, and optional flags:

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" --branch-slug="${BRANCH_SLUG}" --summary="${PLAN_SUMMARY}" ${PLAN_TYPE_FLAG} ${OBJECTIVE_FLAG}
```

Parse the JSON output to extract `plan_number` for verification in Step 3.

If the command fails, display the error and stop.

### Step 3: Verify Objective Link (if applicable)

**Only run this step if `objective_issue` is non-null in the JSON output from Step 2.**

Verify the objective link was saved correctly:

```bash
erk exec get-plan-metadata <plan_number> objective_issue
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
Fix: Close draft PR #<plan_number>,
ensure the objective-context marker exists, and re-run /erk:plan-save.
```

Exit without creating the plan-saved marker. The session continues so the user can retry.

### Step 3.5: Update Objective Roadmap (if objective linked)

**Only run this step if `objective_issue` was non-null in JSON output and verification passed.**

Update the objective's roadmap table to show that a plan has been created for this node:

1. **Read the roadmap node marker** to get the node ID:

```bash
step_id=$(erk exec marker read --session-id "${CLAUDE_SESSION_ID}" roadmap-step)
```

If the marker doesn't exist (command fails), skip this step - the plan wasn't created via `objective-plan`.

2. **Update the roadmap table** using the dedicated command:

```bash
erk exec update-objective-node <objective-issue> --node "$step_id" --pr "#<plan_number>" --status in_progress
```

This atomically fetches the objective body, finds the matching node row, sets the Status cell to `in-progress`, and writes the updated body back.

3. **Report the update:**

Display: `Updated objective #<objective-issue> roadmap: node <step_id> → plan #<plan_number>`

**Error handling:** If the roadmap update fails, warn but continue - the plan was saved successfully, just the roadmap tracking didn't update. The user can manually update the objective.

### Step 4: Display Results

**If JSON contains `skipped_duplicate: true`:**

Display: `Plan already saved as #<plan_number> (duplicate skipped)`

If `branch_name` is present in the JSON, display the same next-steps block as the success case below.

If `branch_name` is absent, display only: `View PR: <plan_url>`

Return immediately (skip Steps 3, 3.5 above if not already executed).

**Otherwise, on success**, display:

```
Plan "<title>" saved as draft PR #<plan_number>
URL: <issue_url>
```

**Slot options block:**

The "OR exit Claude Code first" section should show both slot allocation options, with the recommended one listed first based on trunk detection:

If **on trunk = true**:

```
OR exit Claude Code first, then run one of:

  New slot (recommended — you're on trunk):
    Local: erk br co --new-slot --for-plan <plan_number>
    Implement: source "$(erk br co --new-slot --for-plan <plan_number> --script)" && erk implement --dangerous

  Same slot:
    Local: erk br co --for-plan <plan_number>
    Implement: source "$(erk br co --for-plan <plan_number> --script)" && erk implement --dangerous

  Dispatch to Queue: erk pr dispatch <plan_number>
```

If **on trunk = false**:

```
OR exit Claude Code first, then run one of:

  Same slot (recommended — you're in a slot):
    Local: erk br co --for-plan <plan_number>
    Implement: source "$(erk br co --for-plan <plan_number> --script)" && erk implement --dangerous

  New slot:
    Local: erk br co --new-slot --for-plan <plan_number>
    Implement: source "$(erk br co --new-slot --for-plan <plan_number> --script)" && erk implement --dangerous

  Dispatch to Queue: erk pr dispatch <plan_number>
```

**Next steps block:**

```
Next steps:

View PR: <plan_url>

In Claude Code:
  Dispatch to queue: /erk:pr-dispatch — Dispatch plan for remote agent implementation

OR exit Claude Code first, then run one of:
  Checkout: erk br co --for-plan <plan_number>
  Dispatch to Queue: erk pr dispatch <plan_number>
```

If objective was verified, also display: `Verified objective link: #<objective-number>`

If the JSON output contains `slot_name` and `slot_objective_updated: true`, also display: `Slot objective updated: <slot_name> → #<objective-number>`

**Note:** Slot objective updates are handled automatically by `plan-save` when an objective is linked via the session marker - no separate command call needed.

On failure, display the error message and suggest:

- Checking that a plan exists (enter Plan mode and exit it first)
- Verifying GitHub CLI authentication (`gh auth status`)
- Checking network connectivity

## Session Tracking

After successfully saving a plan, the plan number is stored in a marker file that enables automatic plan updates in the same session.

**To read the saved plan number:**

```bash
erk exec marker read --session-id "${CLAUDE_SESSION_ID}" plan-saved-issue
```

This returns the plan number (exit code 0) or exits with code 1 if no plan was saved in this session.

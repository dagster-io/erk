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
```

Objective linking is automatic: if a plan was created via `/erk:objective-plan`, the session's objective-context marker is read automatically by the save command.

## Plan Storage

The plan is saved using the configured backend:

- **Draft PR backend** (`PLAN_BACKEND = "draft_pr"`): Creates a branch, pushes a plan commit, and opens a draft PR. Plan content is in the PR body after the metadata separator.
- **Issue backend** (`PLAN_BACKEND = "github"`): Creates a GitHub issue. Metadata in the issue body, plan content in the first comment.

The JSON output contract is the same for both backends (`plan_number`, `plan_url`, `title`, `branch_name`, `plan_backend`).

## Agent Instructions

### Step 1: Parse Arguments

Check `$ARGUMENTS` for the `--plan-type` flag:

```
If $ARGUMENTS contains "--plan-type=<type>":
  - Extract the type (standard or learn)
  - Store as PLAN_TYPE variable
  - Set PLAN_TYPE_FLAG to "--plan-type=<type>"
Else:
  - Set PLAN_TYPE_FLAG to empty string
```

### Step 1.5: Generate Branch Slug

Before saving, generate a branch slug from the plan title. Read the plan title from the plan file you wrote in plan mode (the first `# ` heading).

Generate a branch slug from the title:

- 2-4 hyphenated lowercase words, max 30 characters
- Capture distinctive essence, drop filler words (the, a, for, implementation, plan)
- Prefer action verbs: add, fix, refactor, update, consolidate, extract, migrate
- Examples: "fix-auth-session", "add-plan-validation", "refactor-gateway-abc"

Store the result as `BRANCH_SLUG`.

### Step 2: Run Save Command

Run this command with the session ID, branch slug, and optional flags:

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" --branch-slug="${BRANCH_SLUG}" ${PLAN_TYPE_FLAG}
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
Fix: Close <"draft PR" if plan_backend=="draft_pr", else "issue"> #<plan_number>,
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
erk exec update-objective-node <objective-issue> --node "$step_id" --plan "#<plan_number>"
```

This atomically fetches the issue body, finds the matching node row, updates the Plan cell, sets the Status cell to `in-progress`, and writes the updated body back.

3. **Report the update:**

Display: `Updated objective #<objective-issue> roadmap: node <step_id> → plan #<plan_number>`

**Error handling:** If the roadmap update fails, warn but continue - the plan was saved successfully, just the roadmap tracking didn't update. The user can manually update the objective.

### Step 4: Display Results

**If JSON contains `skipped_duplicate: true`:**

Display: `Plan already saved as #<plan_number> (duplicate skipped)`

If `branch_name` is present in the JSON, display the same next-steps block as the success case below (using the `plan_backend` field to choose the correct format).

If `branch_name` is absent, display only: `View PR: <plan_url>`

Return immediately (skip Steps 3, 3.5 above if not already executed).

**Otherwise, on success**, display based on `plan_backend` from JSON output:

**Header (both backends):**

```
Plan "<title>" saved as <"draft PR" if plan_backend=="draft_pr", else "issue"> #<plan_number>
URL: <issue_url>
```

**Slot options block (used by both backends below):**

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

**If `plan_backend` is `"draft_pr"`:**

```
Next steps:

View PR: <plan_url>

In Claude Code:
  Dispatch to queue: /erk:pr-dispatch — Dispatch plan for remote agent implementation

OR exit Claude Code first, then run one of:
  Checkout: erk br co --for-plan <plan_number>
  Dispatch to Queue: erk pr dispatch <plan_number>
```

**If `plan_backend` is `"github"` (or absent):**

```
Next steps:

View Issue: <plan_url>

In Claude Code:
  Dispatch to queue: /erk:pr-dispatch — Dispatch plan for remote agent implementation
  Plan review: /erk:plan-review — Submit plan as PR for human review before implementation

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

After successfully saving a plan, the issue number is stored in a marker file that enables automatic plan updates in the same session.

**To read the saved issue number:**

```bash
erk exec marker read --session-id "${CLAUDE_SESSION_ID}" plan-saved-issue
```

This returns the issue number (exit code 0) or exits with code 1 if no plan was saved in this session.

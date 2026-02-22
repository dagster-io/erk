---
description: Migrate an issue-based plan to a draft-PR-based plan
argument-hint: "<plan_number>"
---

# /erk:migrate-plan-to-draft-pr

Migrate an existing GitHub issue-based erk-plan to the draft PR backend.

## What This Does

1. Reads the plan content and metadata from the specified issue
2. Creates a `plan-{slug}-{timestamp}` branch from trunk
3. Commits `.erk/impl-context/plan.md` to the branch and pushes it
4. Creates a draft PR with the same title, content, labels, and metadata
5. Comments on the original issue with a migration notice and closes it

Preserves: title, plan content, labels (`erk-learn`, etc.), objective link, and `created_from_session`.

## Usage

```bash
/erk:migrate-plan-to-draft-pr 1234
```

## Agent Instructions

### Step 1: Parse Arguments

Extract the issue number from `$ARGUMENTS`.

If no argument is provided, search the conversation from bottom to top for the most recent issue URL or issue number reference and use that.

If still no issue number found, tell the user: "Please provide a plan number: `/erk:migrate-plan-to-draft-pr <plan_number>`"

### Step 2: Preview (optional dry run)

To preview what would happen without making changes:

```bash
erk exec plan-migrate-to-draft-pr <plan_number> --dry-run --format display
```

Display the output to the user and ask if they want to proceed. Skip this step if the user said to proceed directly.

### Step 3: Run the Migration

```bash
erk exec plan-migrate-to-draft-pr <plan_number> --format json
```

Parse the JSON output. If `success` is `false`, display the error and stop.

### Step 4: Display Results

On success, display:

```
Migrated plan #<original_issue_number> → draft PR #<pr_number>
PR URL: <pr_url>
Branch: <branch_name>
Original issue #<original_issue_number> has been closed.

Next steps:
  View PR:  gh pr view <pr_number> --web
  Prepare:  erk br co --for-plan <pr_number>
  Submit:   erk plan submit <pr_number>
```

### Error Cases

- **issue_not_found**: "Issue #N not found. Check the issue number and try again."
- **not_an_erk_plan**: "Issue #N does not have the `erk-plan` label. Only erk-plan issues can be migrated."
- Any other error: Display the error message from the JSON output.

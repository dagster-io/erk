---
description: Submit a saved plan for PR-based review
argument-hint: "[issue-number]"
---

# /erk:review-plan

Submit a saved erk-plan for PR-based review. Creates a temporary PR where reviewers can add inline comments on the plan content.

## Usage

```bash
/erk:review-plan 1234          # Review plan #1234
/erk:review-plan               # Prompt for issue number
```

## Agent Instructions

### Step 1: Parse Issue Number

Parse `$ARGUMENTS` for the issue number:

- If argument is a number, use it directly
- If argument is a GitHub URL, extract issue number from path
- If no argument provided, search conversation for recently mentioned plan issues or prompt with AskUserQuestion

### Step 2: Check for Existing Review

Before creating a new review PR, check if one already exists:

```bash
erk exec get-plan-metadata <issue> review_pr
```

Parse the JSON response:

- If `success: true` and `value` is not null: A review PR already exists
  - Display: "Plan #<issue> already has a review PR: #<value>"
  - Display: "View: gh pr view <value> --web"
  - Exit without creating a new PR
- If `success: false` or `value` is null: No existing review, continue

Then check for a previous completed review:

```bash
erk exec get-plan-metadata <issue> last_review_pr
```

- If `success: true` and `value` is not null: A previous review was completed
  - Display warning: "Plan #<issue> was previously reviewed via PR #<value>"
  - Use AskUserQuestion to ask the user: "Create a new review PR anyway?"
    - Options: "Yes, create new review" / "No, cancel"
  - If user chooses to cancel, exit without creating a new PR
  - If user confirms, continue to Step 3

### Step 3: Create Review Branch

```bash
erk exec plan-create-review-branch <issue>
```

Parse the JSON response. On success, extract:

- `branch` - The created branch name
- `file_path` - The plan file path (e.g., PLAN-REVIEW-1234.md)
- `plan_title` - The plan title from the issue

Error handling:

- `issue_not_found`: "Error: Issue #<issue> not found"
- `missing_erk_plan_label`: "Error: Issue #<issue> is not an erk-plan. Only saved plans can be reviewed."
- `no_plan_content`: "Error: Issue #<issue> has no plan content. Save a plan first with /erk:plan-save"

### Step 4: Create Review PR

```bash
erk exec plan-create-review-pr <issue> <branch> <title>
```

Pass the values extracted from Step 3.

Parse the JSON response. On success, extract:

- `pr_number` - The created PR number
- `pr_url` - The PR URL

Error handling:

- `pr_already_exists`: "Error: A PR already exists for this branch. Check: gh pr list --head <branch>"
- `invalid_issue`: "Error: Issue #<issue> has invalid metadata"

### Step 5: Display Success

```
Plan #<issue> submitted for review

Review PR: #<pr_number>
URL: <pr_url>

Next steps:
1. Share the PR URL with reviewers
2. Reviewers add inline comments on the plan
3. Address feedback: /erk:pr-address (coming in Phase 2)
4. When done: close the PR without merging

View in browser: gh pr view <pr_number> --web
```

## Error Cases

| Scenario          | Action                                                  |
| ----------------- | ------------------------------------------------------- |
| Issue not found   | Display error, suggest checking issue number            |
| Not an erk-plan   | Display error, explain only saved plans can be reviewed |
| No plan content   | Display error, suggest running /erk:plan-save first     |
| PR already exists | Display existing PR number, suggest viewing it          |
| Existing review   | Display existing review PR, exit gracefully             |

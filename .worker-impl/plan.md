# Plan: Create `/erk:review-plan` Skill (Step 1.5)

**Objective:** #6201 - Plan Review via Temporary PR
**Step:** 1.5 - Create `/erk:review-plan` skill that orchestrates the above

## Goal

Create a skill that enables plan review via a temporary PR. The skill orchestrates the three existing exec commands to:
1. Validate the plan issue and check for existing reviews
2. Create a review branch with the plan as a Markdown file
3. Create a draft PR for inline review

## Implementation

### Create File

**Path:** `.claude/commands/erk/review-plan.md`

### Command Structure

```yaml
---
description: Submit a saved plan for PR-based review
argument-hint: "[issue-number]"
---

# /erk:review-plan

Submit a saved erk-plan for PR-based review. Creates a temporary PR where reviewers can add inline comments on the plan content.

## Usage

/erk:review-plan 1234          # Review plan #1234
/erk:review-plan               # Prompt for issue number

## Agent Instructions

### Step 1: Parse Issue Number

Parse `$ARGUMENTS` for the issue number:
- If argument is a number, use it directly
- If argument is a GitHub URL, extract issue number from path
- If no argument provided, search conversation for recently mentioned plan issues or prompt with AskUserQuestion

### Step 2: Check for Existing Review

Before creating a new review PR, check if one already exists:

erk exec get-plan-metadata <issue> review_pr

Parse the JSON response:
- If `success: true` and `value` is not null: A review PR already exists
  - Display: "Plan #<issue> already has a review PR: #<value>"
  - Display: "View: gh pr view <value> --web"
  - Exit without creating a new PR
- If `success: false` or `value` is null: No existing review, continue

### Step 3: Create Review Branch

erk exec plan-create-review-branch <issue>

Parse the JSON response. On success, extract:
- `branch` - The created branch name
- `file_path` - The plan file path (e.g., PLAN-REVIEW-1234.md)
- `plan_title` - The plan title from the issue

Error handling:
- `issue_not_found`: "Error: Issue #<issue> not found"
- `missing_erk_plan_label`: "Error: Issue #<issue> is not an erk-plan. Only saved plans can be reviewed."
- `no_plan_content`: "Error: Issue #<issue> has no plan content. Save a plan first with /erk:plan-save"

### Step 4: Create Review PR

erk exec plan-create-review-pr <issue> <branch> <title>

Pass the values extracted from Step 3.

Parse the JSON response. On success, extract:
- `pr_number` - The created PR number
- `pr_url` - The PR URL

Error handling:
- `pr_already_exists`: "Error: A PR already exists for this branch. Check: gh pr list --head <branch>"
- `invalid_issue`: "Error: Issue #<issue> has invalid metadata"

### Step 5: Display Success

Plan #<issue> submitted for review

Review PR: #<pr_number>
URL: <pr_url>

Next steps:
1. Share the PR URL with reviewers
2. Reviewers add inline comments on the plan
3. Address feedback: /erk:pr-address (coming in Phase 2)
4. When done: close the PR without merging

View in browser: gh pr view <pr_number> --web

## Error Cases

| Scenario | Action |
|----------|--------|
| Issue not found | Display error, suggest checking issue number |
| Not an erk-plan | Display error, explain only saved plans can be reviewed |
| No plan content | Display error, suggest running /erk:plan-save first |
| PR already exists | Display existing PR number, suggest viewing it |
| Existing review | Display existing review PR, exit gracefully |
```

## Design Decisions

1. **No session marker needed** - The `review_pr` field in plan-header metadata already tracks review state
2. **Idempotent** - Step 2 checks for existing review before creating a new one
3. **Skip plan-submit-for-review** - `plan-create-review-branch` already handles fetching/validating plan content internally
4. **Draft PR** - Uses draft mode so reviewers know it's for review, not merge

## Files to Modify

| File | Change |
|------|--------|
| `.claude/commands/erk/review-plan.md` | **Create** - The new skill command |

## Verification

1. **Test on an existing saved plan:**
   - Find or create a plan issue with `/erk:plan-save`
   - Run `/erk:review-plan <issue-number>`
   - Verify PR is created with plan content visible
   - Verify plan issue metadata contains `review_pr` field

2. **Test idempotency:**
   - Run `/erk:review-plan <same-issue>` again
   - Verify it shows existing PR instead of creating a duplicate

3. **Test error cases:**
   - Non-existent issue number
   - Issue without erk-plan label
   - Issue without plan content

## Related Documentation

- Skills: `fake-driven-testing`, `dignified-python` (not needed - no Python code)
- Existing commands to reference: `.claude/commands/erk/plan-save.md`, `.claude/commands/erk/prepare.md`
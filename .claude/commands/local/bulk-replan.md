---
description: Replan multiple erk-plan issues in parallel with batch approval
argument-hint: [--cutoff <issue-number>]
---

# /local:bulk-replan

Bulk replan erk-plan issues with parallel investigation and batch approval.

## Usage

```bash
/local:bulk-replan                # All open erk-plan issues
/local:bulk-replan --cutoff 4343  # Only issues #4343 and older
```

---

## Agent Instructions

### Step 1: Parse Arguments

Extract optional cutoff from `$ARGUMENTS`:

- `--cutoff <number>`: Only process issues with number ≤ cutoff
- No argument: Process all open erk-plan issues

### Step 2: Fetch Open Issues

```bash
gh api repos/dagster-io/erk/issues \
  -X GET \
  --paginate \
  -f labels=erk-plan \
  -f state=open \
  -f per_page=100 \
  --jq 'sort_by(.number) | map({number, title, createdAt: .created_at})'
```

Note: Uses REST API (not `gh issue list`) to avoid GraphQL rate limits.

Filter by cutoff if provided. Display issue count:

```
Found <N> open erk-plan issues to investigate.
```

If more than 10 issues, warn:

```
Warning: Limiting to 10 issues to avoid rate limits. Use --cutoff to target specific ranges.
```

### Step 3: Launch Parallel Investigations

For each issue (max 10), launch a background Explore agent using Task tool with these parameters:

- `subagent_type`: "Explore"
- `run_in_background`: true
- `description`: "Investigate #\<number\>"
- `prompt`: Use the investigation prompt template below

**Investigation Prompt Template:**

> Investigate erk-plan issue #\<number\> to determine its status.
>
> **Investigation Steps:**
>
> 1. Fetch issue details: `gh api repos/dagster-io/erk/issues/<number> --jq '{title: .title, body: .body, labels: [.labels[].name]}'`
> 2. Check if this is actually an erk-plan (not an objective):
>    - If body contains 'erk-objective' or labels include 'erk-objective', this is NOT_AN_ERK_PLAN
> 3. Fetch plan content from first comment: `gh api repos/dagster-io/erk/issues/<number>/comments --jq '.[0].body'`
> 4. Search codebase for implementation evidence:
>    - Extract key file paths, function names, or feature names from plan
>    - Use Glob and Grep to check if expected files/code exist
> 5. Check for related merged PRs: `gh pr list --repo dagster-io/erk --state merged --search 'in:title <keywords>' --json number,title,mergedAt --limit 5`
>
> **Determine Status - Return ONE of:**
>
> - **IMPLEMENTED**: Code exists, found in codebase or merged PR (include PR numbers)
> - **OBSOLETE**: Feature removed, approach abandoned, or no longer relevant (include reason)
> - **NOT_AN_ERK_PLAN**: Wrong label - is objective or other issue type (include what type)
> - **NEEDS_FRESH_PLAN**: Not implemented, original plan is outdated or unclear (include what needs updating)
>
> **Output Format:**
>
> ISSUE: #\<number\>
> TITLE: \<title\>
> STATUS: \<IMPLEMENTED|OBSOLETE|NOT_AN_ERK_PLAN|NEEDS_FRESH_PLAN\>
> ACTION: \<recommended action\>
> EVIDENCE: \<supporting evidence, PR numbers, file paths\>

### Step 4: Collect Results

Use TaskOutput tool to retrieve findings from each agent as they complete.

Build a summary table from the structured findings.

### Step 5: Present Batch Summary

Display table to user:

```markdown
## Investigation Results

| #   | Issue                     | Status           | Recommendation | Evidence         |
| --- | ------------------------- | ---------------- | -------------- | ---------------- |
| 1   | #4235: Add changelog flag | IMPLEMENTED      | Close          | PR #4446         |
| 2   | #4246: Force hint         | IMPLEMENTED      | Close          | PR #4506         |
| 3   | #4284: Docs restructure   | NOT_AN_ERK_PLAN  | Remove label   | Is erk-objective |
| 4   | #4299: Post-init hook     | NEEDS_FRESH_PLAN | Replan         | Not implemented  |
```

Group by status for clarity:

1. **Ready to Close** (IMPLEMENTED, OBSOLETE)
2. **Label Issues** (NOT_AN_ERK_PLAN)
3. **Needs Replanning** (NEEDS_FRESH_PLAN)

### Step 6: Get User Approval

Use AskUserQuestion with these options:

- "Execute all recommendations" - Apply all suggested actions
- "Select specific actions" - Choose which actions to execute
- "Cancel" - Exit without changes

If user selects specific actions, present numbered list and accept comma-separated input via another AskUserQuestion.

### Step 7: Execute Approved Actions

For each approved action:

**Close as implemented:**

```bash
gh api repos/dagster-io/erk/issues/<number>/comments -X POST -f body="Closing as implemented. Evidence: <evidence>"
gh api repos/dagster-io/erk/issues/<number> -X PATCH -f state=closed
```

**Close as obsolete:**

```bash
gh api repos/dagster-io/erk/issues/<number>/comments -X POST -f body="Closing as obsolete: <reason>"
gh api repos/dagster-io/erk/issues/<number> -X PATCH -f state=closed
```

**Remove erk-plan label (for objectives):**

```bash
gh api repos/dagster-io/erk/issues/<number>/labels/erk-plan -X DELETE
```

**Create fresh plan (NEEDS_FRESH_PLAN):**

1. Display: "Creating fresh plan for #<number>..."
2. Run `/local:replan <number>` to create new plan and close original

### Step 8: Display Summary

```
## Bulk Replan Complete

✓ Closed <N> issues as implemented
✓ Closed <N> issues as obsolete
✓ Removed label from <N> issues
✓ Replanned <N> issues

Issues closed: #<list>
Labels removed: #<list>
Replanned: #<original> → #<new> (for each)
```

---

## Error Handling

- If an investigation agent fails or times out, skip that issue and note in summary
- If GitHub API fails, retry once then report error
- If fresh plan creation fails, leave original issue open and report error
- Maximum 10 parallel agents to stay within rate limits

---

## Important Notes

- Parallel agents reduce total time from O(n) to ~O(1) for investigation phase
- User approval is REQUIRED before executing any actions
- Fresh plan creation via `/local:replan` is sequential (each requires plan mode)
- Uses REST API to avoid GraphQL rate limits

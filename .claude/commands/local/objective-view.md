---
description: View progress and associations for an objective issue
---

# /local:objective-view

Displays progress and associations for an objective issue, including roadmap status analysis, associated PRs, and associated plans.

## Usage

```bash
/local:objective-view <issue_number>
```

---

## Agent Instructions

### Step 1: Validate Arguments

Parse `$ARGUMENTS` for the issue number. If no issue number provided, display error:

```
Error: Issue number required.
Usage: /local:objective-view <issue_number>
```

### Step 2: Fetch Objective Issue

```bash
erk exec get-issue-body <issue_number>
```

Parse the JSON output to get:

- `body`: The issue body content
- `title`: The issue title
- `state`: OPEN or CLOSED
- `created_at`: Creation timestamp
- `labels`: List of labels

Verify the issue has the `erk-objective` label. If not:

```
Error: Issue #<number> is not an erk-objective issue (missing erk-objective label).
```

### Step 3: Fetch Comment Count

```bash
gh api repos/dagster-io/erk/issues/<issue_number> --jq '.comments'
```

This returns the comment count directly from the issue.

### Step 4: Fetch Associated PRs

```bash
erk exec get-issue-timeline-prs <issue_number>
```

Parse JSON output to get list of PRs that reference this objective. The output has format:

```json
{
  "success": true,
  "issue_number": 4954,
  "prs": [{ "number": 5054, "state": "MERGED", "is_draft": false }]
}
```

### Step 5: Fetch Associated Plans

```bash
erk exec get-plans-for-objective <issue_number>
```

Parse JSON output to get plans linked to this objective. The output has format:

```json
{
  "success": true,
  "objective_number": 4954,
  "plans": [{ "number": 5066, "state": "OPEN", "title": "P5066: Phase 8..." }]
}
```

Note: This command fetches erk-plan issues and filters by `objective_id` in the plan-header metadata block.

### Step 6: Analyze Roadmap Progress

Use haiku inference (via model parameter in prompts) to analyze the objective body's Roadmap section:

**Prompt to haiku:**

> Analyze this objective issue's Roadmap section. For each phase, identify:
>
> 1. Phase name (e.g., "Phase 1A: Git Gateway Steelthread")
> 2. Total steps in that phase
> 3. Completed steps (status is "done")
> 4. Phase completion status (all steps done = complete)
>
> Return as JSON:
>
> ```json
> {
>   "phases": [
>     {
>       "name": "Phase 1A",
>       "total_steps": 2,
>       "done_steps": 2,
>       "complete": true
>     },
>     {
>       "name": "Phase 1B",
>       "total_steps": 3,
>       "done_steps": 1,
>       "complete": false
>     }
>   ],
>   "total_phases": 2,
>   "complete_phases": 1,
>   "total_steps": 5,
>   "done_steps": 3
> }
> ```
>
> Handle variations in status values:
>
> - done/complete/completed/✅ = done
> - pending/todo/not-started = not done
> - in-progress/wip/active = not done
> - blocked/waiting = not done
> - skipped/n/a = don't count toward total
>
> Objective body:

Pass the objective body content after this prompt.

### Step 7: Calculate Relative Time

Convert `created_at` timestamp to relative time (e.g., "3d ago", "1w ago", "2mo ago").

### Step 8: Display Results

Format output as:

```markdown
## Objective #<number>: <title>

**State:** <OPEN|CLOSED> | **Created:** <relative_time>

### Progress

- **Activities:** <comment_count> comments
- **Roadmap:** <complete_phases>/<total_phases> phases, <done_steps>/<total_steps> steps completed

### Phase Details

| Phase    | Steps      | Status      |
| -------- | ---------- | ----------- |
| Phase 1A | 2/2 (100%) | ✅ Complete |
| Phase 1B | 1/3 (33%)  | In Progress |
| Phase 2A | 0/2 (0%)   | Pending     |

### Associated PRs (<count>)

| #    | State  | Title                     |
| ---- | ------ | ------------------------- |
| #123 | MERGED | Implement Git steelthread |
| #124 | OPEN   | Add FakeGitHub            |

### Associated Plans (<count>)

| #    | State  | Title                         |
| ---- | ------ | ----------------------------- |
| #210 | OPEN   | P210: Phase 2A implementation |
| #211 | CLOSED | P211: Phase 1B completion     |
```

If no associated PRs: `_No associated PRs found._`
If no associated plans: `_No associated plans found._`

### Step 9: Suggest Next Steps

After displaying, suggest relevant actions based on state:

**If objective is OPEN with pending phases:**

```
**Suggested actions:**
- `/erk:objective-next-plan <number>` - Create a plan for the next pending step
- `gh issue view <number> --web` - View full objective in browser
```

**If objective is OPEN with all phases complete:**

```
**All phases complete!** Consider closing this objective:
- `/erk:objective-close <number>` - Close the objective with summary
```

**If objective is CLOSED:**

```
This objective is closed. View history in browser:
- `gh issue view <number> --web`
```

---

## Error Handling

- **Issue not found:** Display "Error: Issue #<number> not found."
- **GitHub API rate limited:** Display "Error: GitHub API rate limited. Try again later."
- **Roadmap parsing fails:** Display roadmap section as-is with note: "Could not parse roadmap structure automatically."

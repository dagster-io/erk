---
description: Replan all open erk-learn plans via consolidation workflow
---

# /local:replan-learn-plans

Queries all open erk-learn plan issues and passes them to `/erk:replan` for consolidation into a single unified documentation plan.

## Rationale

- Learn plans often overlap (multiple sessions may discover similar documentation opportunities)
- One unified documentation plan is cleaner to implement than N separate ones
- Replan consolidation identifies overlap and deduplication opportunities

## Usage

```bash
/local:replan-learn-plans
```

---

## Agent Instructions

### Step 1: Query Open erk-learn Issues

Fetch all open issues with the `erk-learn` label:

```bash
gh api repos/dagster-io/erk/issues \
  -X GET \
  --paginate \
  -f labels=erk-learn \
  -f state=open \
  -f per_page=100 \
  --jq '.[] | {number, title, created_at}'
```

Note: Uses REST API (not `gh issue list`) to avoid GraphQL rate limits.

Store the results as a list of issues with their numbers and titles.

### Step 2: Handle Edge Cases

Based on the number of issues found:

#### 2a: Zero Issues

If no open erk-learn issues found:

```
No open erk-learn plans found. Nothing to replan.
```

Stop here.

#### 2b: One Issue

If exactly one issue found, present it and ask the user:

```
Found 1 open erk-learn plan:

| Issue | Title | Created |
| ----- | ----- | ------- |
| #<number> | <title> | <date> |

This single plan can be replanned to update it against the current codebase.
```

Use AskUserQuestion with options:

- "Replan this issue" - Proceed with single replan
- "Cancel" - Exit without action

If user cancels, stop here.

#### 2c: Multiple Issues

If 2+ issues found, present the list:

```
Found <N> open erk-learn plans:

| Issue | Title | Created |
| ----- | ----- | ------- |
| #<number1> | <title1> | <date1> |
| #<number2> | <title2> | <date2> |
...

These plans will be consolidated into a single unified documentation plan.
```

Use AskUserQuestion with options:

- "Consolidate all plans" - Proceed with consolidation
- "Cancel" - Exit without action

If user cancels, stop here.

### Step 3: Invoke /erk:replan

Build the issue list and invoke the replan skill:

**For single issue:**

```
/erk:replan <issue_number>
```

**For multiple issues:**

```
/erk:replan <issue1> <issue2> <issue3> ...
```

Use the Skill tool with `skill: "erk:replan"` and `args: "<space-separated issue numbers>"`.

**IMPORTANT:** The `/erk:replan` skill will launch background Explore agents for deep investigation. Per Step 4e of that skill, you MUST wait for ALL background agents to complete before creating the consolidated plan. Do not proceed to plan creation until every investigation agent has returned its findings.

---

## Error Handling

- If GitHub API is rate limited, report and stop
- If REST API call fails, display error message and stop

## Related Commands

- `/erk:replan` - Underlying replan/consolidation workflow
- `/local:audit-plans` - Audit all open erk-plan issues
- `/erk:learn` - Generate documentation plans from sessions

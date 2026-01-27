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

Fetch all open issues with the `erk-learn` label, including their full label list for filtering:

```bash
gh api repos/dagster-io/erk/issues \
  -X GET \
  --paginate \
  -f labels=erk-learn \
  -f state=open \
  -f per_page=100 \
  --jq '.[] | {number, title, created_at, labels: [.labels[].name]}'
```

Note: Uses REST API (not `gh issue list`) to avoid GraphQL rate limits.

### Step 1b: Filter Out Already-Consolidated Plans

From the results, filter out any issues that have the `erk-consolidated` label.

These are plans that were themselves created by a previous consolidation and should not be re-consolidated.

If any issues were filtered out, report to user:

```
Filtered out N already-consolidated plan(s): #X, #Y, ...
```

Store the filtered results as a list of issues with their numbers and titles.

### Step 2: Handle Edge Cases

Based on the number of **filtered** issues (after excluding `erk-consolidated`):

#### 2a: Zero Issues

If no open erk-learn issues found (after filtering):

```
No open erk-learn plans found. Nothing to replan.
```

If issues were found but ALL had `erk-consolidated` label:

```
All N open erk-learn plans are already consolidated. Nothing new to consolidate.
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

**IMPORTANT:** The `/erk:replan` skill will launch background Explore agents for deep investigation. Per Step 4e of that skill, you MUST wait for ALL background agents to complete before creating the consolidated plan. Use `timeout: 600000` (10 minutes) when calling TaskOutput to wait for each agent. Do not proceed to plan creation until every investigation agent has returned its findings.

### Step 3.5: Context Preservation for Learn Plans (CRITICAL)

Learn plans document patterns discovered during implementation sessions. When the `/erk:replan` skill creates the consolidated plan, ensure it captures:

#### Session-Derived Insights

- **What was built**: Actual code changes with file paths and line numbers
- **Decisions made**: Architectural choices, API designs, naming conventions
- **Gaps identified**: Documentation needs discovered during implementation

#### Documentation-Specific Context

For each documentation item, include:

- **Target file path**: Where the doc will be created/updated
- **Content source**: Which investigation finding informs this item
- **Related code**: File paths that the documentation describes
- **Category placement**: Where in docs/learned/ hierarchy it belongs

#### Actionable Implementation Steps

Each step should specify:

- Exact file to create/modify
- Content outline or template
- Source references (investigation findings, code locations)
- Verification: How to confirm documentation is accurate

**Example of comprehensive learn plan step:**

```markdown
### Step 3: Create flatten-subgateway-pattern.md

**File:** `docs/learned/architecture/flatten-subgateway-pattern.md`

**Content outline:**

1. Problem: Nested subgateways (e.g., `git.branch.branch`) create confusing API
2. Pattern: Flatten to single level (`git.branch`)
3. Implementation: Phase 2A (PR #6159) and Phase 2B (PR #6162)
4. Examples: Before/after code showing the transformation
5. Tripwire: Add to tripwires-index.md under "Gateway Patterns"

**Source:** Investigation of #6160 and #6163 found 14 query methods and 5 mutation methods moved

**Verification:** Document accurately describes the pattern shown in `src/erk/gateway/git/branch.py`
```

---

## Error Handling

- If GitHub API is rate limited, report and stop
- If REST API call fails, display error message and stop

## Related Commands

- `/erk:replan` - Underlying replan/consolidation workflow
- `/local:audit-plans` - Audit all open erk-plan issues
- `/erk:learn` - Generate documentation plans from sessions

# Plan Update Workflow

This document describes the complete workflow for updating an existing plan.

## When to Update vs Create New

| Scenario                      | Action                 | Rationale                 |
| ----------------------------- | ---------------------- | ------------------------- |
| Typos, clarifications         | Update                 | Preserves PR history      |
| Adding implementation details | Update                 | Same plan, more context   |
| Plan fundamentally wrong      | `/erk:replan`          | Creates new with analysis |
| Major scope change            | Create new, close old  | Different work item       |
| Plan partially implemented    | Update remaining steps | Continue tracking         |

## Update Workflow Steps

### Step 1: Get the Existing Plan Content

If you don't have the plan content locally, fetch it from GitHub:

```bash
# Get plan with comments
gh pr view 123 --comments --json comments,body

# The plan content is in the first comment's plan-body block
```

Parse the first comment to extract content between:

```
<!-- erk:metadata-block:plan-body -->
...plan content...
<!-- /erk:metadata-block:plan-body -->
```

### Step 2: Modify the Plan

Option A: **Enter plan mode**

- Make modifications in plan mode
- Plan will be saved to `~/.claude/plans/`

Option B: **Edit directly**

- Modify the plan file at `~/.claude/plans/<slug>.md`

### Step 3: Update the Plan

```bash
# Via slash command (extracts session ID automatically)
/local:plan-update 123

# Via CLI (requires explicit session ID)
erk exec plan-update --pr-number 123 --session-id="<session-id>"

# With explicit plan file
erk exec plan-update --pr-number 123 --plan-path /path/to/plan.md
```

### Step 4: Document the Change (Optional)

Add a comment explaining what changed:

```bash
gh pr comment 123 --body "Updated plan:
- Added step 3 for edge case handling
- Clarified testing requirements"
```

## Integration with `.erk/impl-context/`

When working in a worktree with `.erk/impl-context/<branch>/ref.json`:

```json
{
  "plan_id": 123,
  "plan_url": "https://github.com/owner/repo/pull/123"
}
```

The plan-update command can use this context:

1. Read plan ID from `.erk/impl-context/<branch>/ref.json`
2. Update that PR with current plan content
3. Continue implementation

## Error Handling

| Error            | Cause                         | Solution                 |
| ---------------- | ----------------------------- | ------------------------ |
| "No plan found"  | No plan in `~/.claude/plans/` | Enter plan mode first    |
| "Plan not found" | Wrong plan number             | Verify with `gh pr view` |
| "No comments"    | Issue has no comments         | May be wrong issue type  |

## Examples

### Example: Adding Implementation Details

```bash
# 1. Fetch current plan
gh pr view 42 --comments --json comments

# 2. Enter plan mode, add details about discovered API quirks

# 3. Update the plan
/local:plan-update 42

# 4. Add changelog comment
gh pr comment 42 --body "Added API rate limit handling to step 2"
```

### Example: Correcting a Mistake

```bash
# 1. Edit plan directly
vim ~/.claude/plans/my-plan.md

# 2. Update plan
erk exec plan-update --pr-number 42 --plan-path ~/.claude/plans/my-plan.md
```

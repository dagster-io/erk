# /erk:objective-update

Interactive workflow for updating an objective after landing a linked plan's PR.

## When to Use

Invoke this command when:

1. `erk pr land` detected a linked objective and you chose "Interactive" mode
2. You want to manually update an objective after landing a plan PR

## Workflow

### Step 1: Read Landed Plan State

Read the landing context from scratch storage:

```bash
cat .erk/scratch/sessions/$SESSION_ID/last-landed-plan.json
```

Expected structure:

```json
{
  "plan_issue": 123,
  "objective_issue": 42,
  "pr_number": 456,
  "pr_title": "Add new feature"
}
```

### Step 2: Fetch Objective Details

```bash
gh issue view $OBJECTIVE_ISSUE --json title,body,url
```

### Step 3: Analyze Changes

Review what was accomplished in the merged PR:

- Read PR description and commits
- Understand which roadmap step(s) were addressed

### Step 4: Draft Action Comment

Create an action comment following the objective format:

```markdown
## Action: [Brief title]

**Date:** YYYY-MM-DD
**PR:** #[pr_number]
**Phase/Step:** [from roadmap]

### What Was Done

- [Concrete actions taken]

### Lessons Learned

- [Insights for future work]

### Roadmap Updates

- Step X: pending → done
```

### Step 5: Post Comment and Update Body

1. Post the action comment:

   ```bash
   gh issue comment $OBJECTIVE_ISSUE --body "$COMMENT"
   ```

2. Prompt user to update the objective body (roadmap status):
   ```bash
   gh issue view $OBJECTIVE_ISSUE --web
   ```

## Resources

For objective format details, load the `objective` skill.

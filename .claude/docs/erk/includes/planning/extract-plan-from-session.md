# Extract Plan from Plans Directory

Use the kit CLI to extract the latest plan from `~/.claude/plans/`:

```bash
# Extract plan using kit CLI
plan_result=$(erk kit exec erk save-plan-from-session --extract-only --format json 2>&1)
```

**Parse the result:**

```bash
# Check if extraction succeeded
if echo "$plan_result" | jq -e '.success' > /dev/null 2>&1; then
    # SUCCESS: Extract plan content and title
    plan_content=$(echo "$plan_result" | jq -r '.plan_content')
    plan_title=$(echo "$plan_result" | jq -r '.title')
else
    # FAILURE: Report error
    error_msg=$(echo "$plan_result" | jq -r '.error // "Unknown error"')
    echo "❌ Error: Failed to extract plan"
    echo "Details: $error_msg"
fi
```

**If no plan found:**

```
❌ Error: No plan found in ~/.claude/plans/

This command requires a plan created with ExitPlanMode. To fix:

1. Create a plan (enter Plan mode if needed)
2. Exit Plan mode using the ExitPlanMode tool
3. Run this command again

The plan will be extracted from ~/.claude/plans/ automatically.
```

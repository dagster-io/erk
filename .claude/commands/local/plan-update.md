---
description: Update an existing plan with the current session's plan
argument-hint: <plan-number>
---

# /local:plan-update

Update an existing plan with the current session's plan content.

## Usage

```bash
/local:plan-update 42
/local:plan-update https://github.com/owner/repo/issues/42
```

---

## Agent Instructions

### Step 1: Parse Plan Number

Extract the plan number from the argument:

- If numeric (e.g., `42`), use directly
- If URL (e.g., `https://github.com/owner/repo/pull/42`), extract the number from the path

If no argument provided, check `ref.json` in `.erk/impl-context/<branch>/` for a linked plan number.

If still no plan number, ask the user for the plan number.

### Step 2: Generate Plan Summary

Generate a 2-3 sentence summary of the plan content. Focus on WHAT the plan does and WHY. Plain text, no markdown formatting. Store the result in `PLAN_SUMMARY`.

### Step 3: Run Update Command

```bash
erk exec plan-update --plan-number <plan> --format display --session-id="${CLAUDE_SESSION_ID}" --summary="${PLAN_SUMMARY}"
```

### Step 4: Display Results

On success with `--format display`, display the command output verbatim. On success with `--format json`, parse the JSON and display:

- If `branch_updated` is true: `"Plan updated on PR #N (branch synced)"`
- If `branch_name` is null: `"Plan updated on #N"`
- If `branch_name` is set but `branch_updated` is false: `"Plan updated on PR #N (warning: branch push failed)"`

On failure, display the error and suggest:

- Checking that a plan exists (enter plan mode and exit it first)
- Verifying the plan number is correct (`gh pr view <number>`)
- Checking GitHub CLI authentication (`gh auth status`)

---

## Related

- `/erk:plan-save` - Create new plan (instead of updating)
- `/erk:replan` - Recreate an obsolete plan from scratch
- `erk-planning` skill - Complete plan management documentation

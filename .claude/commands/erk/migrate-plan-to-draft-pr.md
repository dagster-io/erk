# Migrate Issue Plan to Draft PR

Migrate an existing issue-based plan to a draft PR plan.

## Usage

```
/erk:migrate-plan-to-draft-pr <issue_number>
```

## Agent Instructions

### Step 1: Parse Arguments

Extract the issue number from `$ARGUMENTS`. If not provided or not numeric, ask the user for the issue number.

### Step 2: Run Migration

Execute the migration command:

```bash
erk exec plan-migrate-to-draft-pr $ARGUMENTS --format json
```

### Step 3: Display Result

Parse the JSON output and display:

- **On success**: Show the original issue number (now closed), new draft PR number and URL, and branch name
- **On error**: Show the error message

### Step 4: Suggest Next Steps

After successful migration, suggest:

- `erk prepare <pr_number>` to set up a worktree for implementation
- `gh pr view <pr_number> --web` to view the draft PR in the browser

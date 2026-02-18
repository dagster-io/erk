# /erk:migrate-objective-schema

Batch-migrate all open objectives from schema v2 to v3.

## Agent Instructions

### Step 1: List Open Objectives

```bash
gh issue list --label erk-objective --state open --limit 100 --json number,title
```

Parse the JSON output to get the list of objective issue numbers and titles.

If no objectives are found, report "No open objectives found" and stop.

### Step 2: Dry-Run Each Objective

For each objective, run the migration in dry-run mode to identify which ones need migration:

```bash
erk exec migrate-objective-schema <number> --dry-run
```

Parse the JSON output. Categorize each objective into:

- **Needs migration**: `migrated: true` (currently v2)
- **Already v3**: `migrated: false` (nothing to do)
- **Error**: `success: false` (report the error)

### Step 3: Report and Confirm

Display a summary table:

```
Objectives needing migration (v2 -> v3):
  #1234 - Objective Title A
  #5678 - Objective Title B

Already v3 (no action needed):
  #9012 - Objective Title C

Errors:
  #3456 - No roadmap block found
```

Ask the user for confirmation before proceeding with the actual migration.

### Step 4: Migrate Confirmed Objectives

For each objective that needs migration:

```bash
erk exec migrate-objective-schema <number>
```

Parse the JSON output and track results.

### Step 5: Report Summary

```
Migration complete:
  Migrated: N objectives
  Already v3: M objectives
  Errors: K objectives
```

List any errors with their issue numbers and error messages.

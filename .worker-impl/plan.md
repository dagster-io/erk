# Plan: Hide PR/Checks Columns When -P Flag Not Used

## Problem

The `erk ls` command always displays `pr` and `chks` columns even when the `-P` flag is not provided. When `-P` is not used, these columns show `-` for every row, wasting screen space.

## Current Behavior

```
┃ plan  ┃ title    ┃ pr ┃ chks ┃ local-wt ┃ local-run ┃
│ #1639 │ Plan...  │ -  │ -    │ -        │ -         │
```

The columns are always present but contain only `-` when no PR data is fetched.

## Desired Behavior

Without `-P`:

```
┃ plan  ┃ title    ┃ local-wt ┃ local-run ┃
│ #1639 │ Plan...  │ -        │ -         │
```

With `-P`:

```
┃ plan  ┃ title    ┃ pr     ┃ chks ┃ local-wt ┃ local-run ┃
│ #1639 │ Plan...  │ #42 👀 │ ✅   │ -        │ -         │
```

## Solution

Apply the same pattern used for `--runs` flag to the `--prs` flag in `/Users/schrockn/code/erk/src/erk/cli/commands/plan/list_cmd.py`.

### Changes Required

**File: `src/erk/cli/commands/plan/list_cmd.py`**

1. **Lines 286-296 - Conditional column addition:**

   Change from:

   ```python
   table.add_column("plan", style="cyan", no_wrap=True)
   table.add_column("title", no_wrap=True)
   table.add_column("pr", no_wrap=True)
   table.add_column("chks", no_wrap=True)
   table.add_column("local-wt", no_wrap=True)
   table.add_column("local-run", no_wrap=True)
   if runs:
       table.add_column("run-id", no_wrap=True)
       table.add_column("run-state", no_wrap=True, width=12)
   ```

   To:

   ```python
   table.add_column("plan", style="cyan", no_wrap=True)
   table.add_column("title", no_wrap=True)
   if prs:
       table.add_column("pr", no_wrap=True)
       table.add_column("chks", no_wrap=True)
   table.add_column("local-wt", no_wrap=True)
   table.add_column("local-run", no_wrap=True)
   if runs:
       table.add_column("run-id", no_wrap=True)
       table.add_column("run-state", no_wrap=True, width=12)
   ```

2. **Lines 378-398 - Conditional row data:**

   Update the `table.add_row()` calls to conditionally include PR columns:

   ```python
   # Build row based on which columns are enabled
   row = [issue_id, title]
   if prs:
       row.extend([pr_cell, checks_cell])
   row.extend([worktree_name_cell, local_run_cell])
   if runs:
       row.extend([run_id_cell, run_outcome_cell])
   table.add_row(*row)
   ```

## Testing

Run `erk ls` without `-P` flag and verify `pr`/`chks` columns are not shown.
Run `erk ls -P` and verify `pr`/`chks` columns appear with data.

# Fix file list indentation in manifest summary table

## Context

PR #8990 fixed indentation in `_log_learn_pr_files` but the *actual* issue is in `_log_session_summary_from_manifest` — the per-session XML file names are rendered inside a Rich `Table` in the last column ("Size"), causing them to be aligned far to the right. The user wants these file names indented 4 spaces from the far left margin.

## Change

**File:** `src/erk/cli/commands/land_learn.py` line 144

Move file content from column 6 to column 1 with 4-space indent:

```python
# Before:
table.add_row("", "", "", "", "", f"[dim]{filename}  ({file_size_str})[/dim]")

# After:
table.add_row(f"    [dim]{filename}  ({file_size_str})[/dim]", "", "", "", "", "")
```

Rich auto-expands column 1 to fit the long filename, and it starts at the left margin.

**File:** `tests/unit/cli/commands/land/test_land_learn.py`

Update `test_log_session_summary_from_manifest_shows_per_file_sizes` to assert file lines start with 4-space indent (not deep in the table).

## Verification

- Run `pytest tests/unit/cli/commands/land/test_land_learn.py -k "manifest"` via devrun agent

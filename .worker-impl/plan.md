# Add `--all/-a` Flag to `erk ls`

## Summary

Add a convenience flag `--all` (short: `-a`) to the `erk ls` command that enables both `-P` (prs) and `-r` (runs) flags, showing the complete table output.

## Implementation

### File: `src/erk/cli/commands/plan/list_cmd.py`

**1. Add `--all` option to `plan_list_options` decorator (after line 183):**

```python
f = click.option(
    "--all",
    "-a",
    "show_all",  # Use 'show_all' to avoid shadowing Python built-in 'all'
    is_flag=True,
    default=False,
    help="Show all columns (equivalent to -P -r)",
)(f)
```

**2. Update `list_plans` function signature (line 400-408):**

Add `show_all: bool` parameter.

**3. Add flag expansion in `list_plans` (after line 420, before calling `_list_plans_impl`):**

```python
# Handle --all flag (equivalent to -P -r)
if show_all:
    prs = True
    runs = True
```

**4. Update docstring examples (line 409-419):**

Add example: `erk plan list --all` or `erk ls -a`

### File: `tests/commands/plan/test_list.py`

**Add test for the new flag:**

```python
def test_list_plans_all_flag_shows_all_columns() -> None:
    """Test that --all flag enables both PR and run columns."""
    # Arrange: Create plan with PR and workflow run data
    # Act: Invoke with --all flag
    # Assert: Verify both PR columns (pr, chks) and run columns (run-id, run-state) appear
```

## Verification

After implementation:
- `erk ls -a` should show: plan, title, pr, chks, local-wt, local-run, run-id, run-state
- `erk ls --all` should produce identical output
- Existing flags `-P` and `-r` continue to work independently
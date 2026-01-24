# Plan: Add --plan-file option to validate-plan-content

## Summary

Add a `--plan-file` option to the `validate-plan-content` exec command, allowing users to pass a file path directly instead of piping content through stdin.

## Changes

### 1. Modify `src/erk/cli/commands/exec/scripts/validate_plan_content.py`

- Add `--plan-file` option with `type=click.Path(exists=True)`
- When `--plan-file` is provided, read content from the file
- When not provided, fall back to reading from stdin (current behavior)
- Update docstring and help text

```python
@click.command(name="validate-plan-content")
@click.option(
    "--plan-file",
    type=click.Path(exists=True, path_type=Path),
    help="Path to plan file. If not provided, reads from stdin.",
)
def validate_plan_content(*, plan_file: Path | None) -> None:
    if plan_file:
        content = plan_file.read_text()
    else:
        content = sys.stdin.read()
    # rest of logic unchanged
```

### 2. Add tests to `tests/unit/cli/commands/exec/scripts/test_validate_plan_content.py`

- Test `--plan-file` with valid file
- Test `--plan-file` with nonexistent file (click handles error)
- Test that stdin still works when `--plan-file` not provided

## Verification

```bash
# Test with file
erk exec validate-plan-content --plan-file path/to/plan.md

# Test stdin still works
echo "# Test" | erk exec validate-plan-content

# Run unit tests
uv run pytest tests/unit/cli/commands/exec/scripts/test_validate_plan_content.py -v
```

## Files to Modify

- `src/erk/cli/commands/exec/scripts/validate_plan_content.py`
- `tests/unit/cli/commands/exec/scripts/test_validate_plan_content.py`
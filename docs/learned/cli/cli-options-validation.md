---
title: CLI Options Validation
read_when:
  - "adding new CLI options or flags"
  - "implementing option validation logic"
  - "encountering unvalidated user input"
tripwires:
  - action: "adding new CLI flags without validation"
    warning: "Check if validation logic is needed when adding new flags. Boolean flags rarely need validation, but flags accepting values (paths, names, numbers) should validate constraints."
---

# CLI Options Validation

When adding new CLI options, consider whether validation logic is needed to provide helpful error messages for invalid input.

## The Decision Tree

```
Is the new option a boolean flag (--verbose, --force)?
├─ YES → No validation needed
│
└─ NO → Does it accept user-provided values?
    ├─ YES → Add validation
    └─ NO → No validation needed
```

## What Needs Validation

Options that accept values should validate:

### Paths

```python
@click.option("--config", type=click.Path(exists=True))
def command(config: str) -> None:
    """Command that needs a config file."""
    # Click validates that the path exists
```

### Enums/Choices

```python
@click.option("--format", type=click.Choice(["json", "yaml", "text"]))
def command(format: str) -> None:
    """Command with format option."""
    # Click validates the choice
```

### Numbers with Constraints

```python
@click.option("--timeout", type=click.IntRange(min=1, max=3600))
def command(timeout: int) -> None:
    """Command with timeout option."""
    # Click validates the range
```

### Custom Validation

For complex constraints, validate early in the command:

```python
@click.option("--branch", type=str)
def command(branch: str) -> None:
    """Command that needs a valid branch name."""
    if not is_valid_branch_name(branch):
        raise UserFacingCliError(
            f"Invalid branch name: {branch}. "
            f"Branch names cannot contain spaces or special characters."
        )
    # Continue with validated input
```

## What Doesn't Need Validation

- **Boolean flags**: `--verbose`, `--force`, `--dry-run`
- **Optional strings without constraints**: `--message`
- **Options with defaults**: Click handles missing values

## Error Handling

For validation failures, use `UserFacingCliError` (not `RuntimeError` - see [CLI Error Handling Anti-Patterns](error-handling-antipatterns.md)):

```python
from erk.cli.exceptions import UserFacingCliError

if not is_valid(value):
    raise UserFacingCliError(f"Invalid value: {value}. Expected format: ...")
```

## Testing Validation

Always test validation logic:

```python
def test_invalid_timeout_rejected():
    """Verify timeout must be positive."""
    result = runner.invoke(command, ["--timeout", "0"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output
```

## Related Documentation

- [CLI Error Handling Anti-Patterns](error-handling-antipatterns.md) - When to use UserFacingCliError vs RuntimeError
- [CLI Development](cli-development.md) - General CLI development patterns

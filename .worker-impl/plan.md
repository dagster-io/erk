# Plan: Add `--body-file` to `erk exec update-issue-body`

## Summary

Add `--body-file` option to read body content from a file, making it easier to update issues with large markdown bodies that contain special characters.

## Files to Modify

| File                                                             | Changes                  |
| ---------------------------------------------------------------- | ------------------------ |
| `src/erk/cli/commands/exec/scripts/update_issue_body.py`         | Add `--body-file` option |
| `tests/unit/cli/commands/exec/scripts/test_update_issue_body.py` | Add tests                |

## Implementation

### update_issue_body.py

```python
from pathlib import Path

@click.command(name="update-issue-body")
@click.argument("issue_number", type=int)
@click.option("--body", help="New body content")
@click.option("--body-file", type=click.Path(exists=True, path_type=Path), help="Read body from file")
@click.pass_context
def update_issue_body(
    ctx: click.Context,
    issue_number: int,
    *,
    body: str | None,
    body_file: Path | None,
) -> None:
    """Update an issue's body using REST API (avoids GraphQL rate limits)."""
    # Mutual exclusivity validation
    if body is not None and body_file is not None:
        click.echo(json.dumps({"success": False, "error": "Cannot specify both --body and --body-file"}))
        raise SystemExit(1) from None

    if body is None and body_file is None:
        click.echo(json.dumps({"success": False, "error": "Must specify --body or --body-file"}))
        raise SystemExit(1) from None

    # Read from file if specified
    if body_file is not None:
        body = body_file.read_text(encoding="utf-8")

    # ... rest of existing code unchanged
```

## Test Requirements

Add to `test_update_issue_body.py`:

1. **`test_update_issue_body_from_file`**: Read body from file
2. **`test_update_issue_body_fails_with_both_body_and_file`**: Mutual exclusivity
3. **`test_update_issue_body_fails_without_body_or_file`**: Both missing

## Verification

```bash
pytest tests/unit/cli/commands/exec/scripts/test_update_issue_body.py -v
```

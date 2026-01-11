# Plan: Unhide Objective Group

## Summary

Make the `objective` CLI command group visible in `erk --help` output by removing the `hidden=True` parameter.

## Change

**File:** `src/erk/cli/commands/objective/__init__.py`

Change line 11 from:
```python
@click.group("objective", cls=ErkCommandGroup, hidden=True)
```

To:
```python
@click.group("objective", cls=ErkCommandGroup)
```

## Verification

Run `erk --help` and confirm "objective" appears in the command list.
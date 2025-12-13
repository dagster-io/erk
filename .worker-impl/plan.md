# Plan: Add Title to plan-save-to-issue Display Output

## Summary
Add the plan/issue title to the display format output of `erk plan-save-to-issue --format display`.

## Current Behavior
```
Plan saved to GitHub issue #3156
URL: https://github.com/dagster-io/erk/issues/3156
Enrichment: No
Session context: 6 chunks
```

## Desired Behavior
```
Plan saved to GitHub issue #3156: <title here>
URL: https://github.com/dagster-io/erk/issues/3156
Enrichment: No
Session context: 6 chunks
```

## File to Modify
`packages/erk-kits/src/erk_kits/data/kits/erk/scripts/erk/plan_save_to_issue.py`

## Change
Line 186, change:
```python
click.echo(f"Plan saved to GitHub issue #{result.issue_number}")
```

To:
```python
click.echo(f"Plan saved to GitHub issue #{result.issue_number}: {result.title}")
```

## Notes
- `result.title` is already available (it's included in the JSON output format)
- No new data fetching required
- No test changes needed (this is output formatting)
# Plan: Include Plan Title in plan-save Output

## Summary
Update the `/erk:plan-save` command to include the plan title in the success output, providing critical context to the user.

## Problem
The JSON response from `erk exec plan-save-to-issue` includes a `title` field:
```json
{
  "success": true,
  "issue_number": 4862,
  "issue_url": "https://github.com/dagster-io/erk/issues/4862",
  "title": "Changelog Update Plan",  // <-- This exists but isn't displayed
  ...
}
```

But the display template in Step 5 doesn't include it, so users see:
```
Plan saved as issue #4862
URL: https://github.com/dagster-io/erk/issues/4862
```

Instead of the more informative:
```
Plan "Changelog Update Plan" saved as issue #4862
URL: https://github.com/dagster-io/erk/issues/4862
```

## Files to Modify

`.claude/commands/erk/plan-save.md` - Update Step 5 display template

## Changes

Update Step 5 display template from:
```
Plan saved as issue #<issue_number>
URL: <issue_url>
```

To:
```
Plan "<title>" saved as issue #<issue_number>
URL: <issue_url>
```

## Verification
- Run `/erk:plan-save` in a session with a plan
- Confirm the output includes the plan title
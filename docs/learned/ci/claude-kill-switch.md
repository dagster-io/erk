---
title: Claude Kill Switch
read_when:
  - "modifying CI workflows that invoke Claude"
  - "understanding how to emergency-disable Claude in CI"
  - "working with the CLAUDE_ENABLED variable"
tripwires:
  - action: "adding a new CI job that invokes Claude without checking CLAUDE_ENABLED"
    warning: "All Claude CI jobs must check vars.CLAUDE_ENABLED != 'false' before invoking Claude. See claude-kill-switch.md."
---

# Claude Kill Switch

Emergency mechanism to disable Claude inference in CI/CD pipelines.

## Mechanism

The `CLAUDE_ENABLED` GitHub repository variable controls whether Claude-powered CI jobs run.

## Implementation

CI workflows check the variable in job conditions:

```yaml
if: vars.CLAUDE_ENABLED != 'false'
```

This expression:

- **Variable not set**: Job runs (default behavior, treated as truthy)
- **Variable set to `'false'`**: Job is skipped
- **Any other value**: Job runs

## Affected Workflows

- `.github/workflows/ci.yml` — Gates the `autofix` job (Claude-driven CI fixes) at line 153
- `.github/workflows/code-reviews.yml` — Gates code review discovery at line 11

The autofix job has additional conditions beyond the kill switch:

- Not on `master` or `main` branch
- Not a draft PR
- Not labeled with `erk-plan-review`
- At least one CI check failed

## Admin Command

`erk admin gh-actions-api-key` can toggle the API key used by Claude in CI, providing another mechanism for controlling Claude's CI access.

## Related Topics

- [CI Documentation](index.md) - General CI patterns

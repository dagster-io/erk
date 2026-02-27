# Disable CI Autofix Job

## Context
The autofix job in `.github/workflows/ci.yml` automatically launches Claude to fix CI failures (lint, format, type errors, etc.). User wants to temporarily disable this feature without deleting the code.

## Change
**File:** `.github/workflows/ci.yml` (line 162)

Add `false &&` to the beginning of the autofix job's `if` condition to short-circuit it:

```yaml
    if: |
      false &&
      vars.CLAUDE_ENABLED != 'false' &&
      ...
```

This keeps all the autofix code intact but ensures the job never runs.

## Verification
- Push the change and confirm the autofix job shows as skipped in CI runs

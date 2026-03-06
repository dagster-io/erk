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

- `.github/workflows/ci.yml` — Gates `ci-summarize`
- `.github/workflows/code-reviews.yml` — Gates review discovery
- `.github/workflows/learn.yml` — Gates learning runs
- `.github/workflows/one-shot.yml` — Gates one-shot execution
- `.github/workflows/plan-implement.yml` — Gates remote plan implementation
- `.github/workflows/pr-address.yml` — Gates PR feedback handling
- `.github/workflows/pr-rebase.yml` — Gates PR rebases
- `.github/workflows/pr-rewrite.yml` — Gates PR rewrites

Disabling Claude does **not** disable repo validation. `ci.yml` still runs formatting, lint, docs, type checks, and tests; only Claude-powered jobs are skipped.

## Admin Command

`erk admin gh-actions-api-key` can toggle the API key used by Claude in CI, providing another mechanism for controlling Claude's CI access.

## Related Topics

- [CI Documentation](index.md) - General CI patterns

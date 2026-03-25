---
title: "Git Pre-Push Validation"
read_when:
  - "setting up git hooks"
  - "understanding pre-push validation"
  - "bypassing local checks"
  - "modifying pre-push checks"
tripwires:
  - action: "adding a new check to pre-push without updating the Makefile target"
    warning: "Pre-push checks are defined in the Makefile pre-push-check target. The githooks/pre-push script delegates to make pre-push-check."
---

# Git Pre-Push Validation

Local pre-push hook that runs lint, format, and type checks before pushing.

## Setup

```bash
make install-hooks
```

This sets `core.hooksPath = githooks` in the local git config. Must be run once per clone — not automatic.

## Hook Script

**Source**: `githooks/pre-push`

The hook delegates to the Makefile:

```bash
make pre-push-check
```

If the check fails, the push is blocked with an error message.

## Checks Run

**Source**: `Makefile` (`pre-push-check` target)

Three checks run in sequence:

1. **Ruff lint check** — `ruff check`
2. **Ruff format check** — `ruff format --check`
3. **Type check** — `ty check`

Exit codes are aggregated: if any check fails, the overall target exits non-zero.

## Bypass

```bash
git push --no-verify
gt submit --no-verify
```

## Relationship to CI

The pre-push hook runs the same checks as CI, providing faster local feedback. Failing locally prevents wasted CI cycles.
